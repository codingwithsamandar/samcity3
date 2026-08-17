"""jobs bo'limi — ish e'lonlari va rezyumelar: qidirish + joylash.

  search_jobs     — vakansiya qidirish (o'qish, link_list)
  search_resumes  — rezyume qidirish (o'qish)
  post_job        — YANGI vakansiya joylash (mutating → confirm → JobAd)
  post_resume     — YANGI rezyume joylash (mutating → confirm → ResumeAd)

`main.models.JobAd`/`ResumeAd` va `engine._search_jobs` qayta ishlatiladi.
"""

from django.db import transaction
from django.db.models import Q

from .. import engine, selection as sel, ui
from ..registry import executor, propose, tool

JOB_TYPES = ['full_time', 'part_time', 'remote', 'contract', 'temporary']
_JT_LABEL = {'full_time': "To'liq stavka", 'part_time': 'Yarim stavka',
             'remote': 'Masofaviy', 'contract': 'Shartnoma', 'temporary': 'Vaqtinchalik'}


def _som(v):
    try:
        return f"{int(v):,}".replace(',', ' ') + " so'm"
    except (TypeError, ValueError):
        return str(v)


def _salary(lo, hi):
    if lo and hi:
        return f"{_som(lo)}–{_som(hi)}"
    if lo:
        return f"{_som(lo)} dan"
    return ''


# ResumeAd.EXP_CHOICES kalitlari, ENG PAST → ENG YUQORI tartibда (>= filtri uchun).
RESUME_EXP = ['no_exp', '1_year', '1_3', '3_5', '5_plus']
_EXP_LABEL = {'no_exp': 'Tajribasiz', '1_year': '1 yilgacha', '1_3': '1–3 yil',
              '3_5': '3–5 yil', '5_plus': '5+ yil'}


def _map_experience(val):
    """Tabiiy tilni tajriba darajasiga (choice) map qiladi. Tushunmasa None.

    «tajribasiz»→no_exp, «5 yildan ko'p»/«katta tajribali»→5_plus, «3 yil»→1_3.
    """
    import re
    s = str(val or '').strip().lower()
    if not s:
        return None
    if s in RESUME_EXP:
        return s
    if 'tajribasiz' in s or 'boshlovchi' in s:
        return 'no_exp'
    if 'katta tajriba' in s or 'ko\'p tajriba' in s or 'kop tajriba' in s:
        return '5_plus'
    m = re.search(r'\d+', s)
    n = int(m.group()) if m else None
    if n is None:
        return None
    if n <= 0:
        return 'no_exp'
    if n <= 1:
        return '1_year'
    if n <= 3:
        return '1_3'
    if n <= 5:
        return '3_5'
    return '5_plus'


# ── search_jobs ──────────────────────────────────────────────────────────────

@tool(
    section='jobs', action='search_jobs',
    description="Vakansiya qidiradi. Saytda kam natija bo'lsa yoki «internetdan "
                "qidir» desa external=true (HH.uz, OLX qo'shiladi).",
    params={
        'query': ('str', True, "kasb/soha, masalan «dasturchi»"),
        'external': ('bool', False, "tashqi saytlardan ham qidirish"),
    },
)
def search_jobs(ctx, query, external=None):
    from django.conf import settings

    jobs = engine._search_jobs(query, limit=8)

    min_local = int(getattr(settings, 'ASSISTANT_EXTERNAL_MIN_LOCAL', 4))
    want_external = bool(external) or (len(jobs) < min_local)

    ext_listings = []
    if want_external:
        try:
            from .. import external as ext_mod
            ext_listings = ext_mod.search(query, limit=6, domain='jobs')
        except Exception:  # noqa: BLE001 — tashqi qidiruv chatni buzmasin
            ext_listings = []

    # Tashqi natija yo'q, lekin sayt vakansiyalari bor — eski TANLANADIGAN oqim.
    if not ext_listings and jobs:
        items = [_job_pick_item(j, i) for i, j in enumerate(jobs, start=1)]
        ss = sel.create(ctx, 'jobs', items)
        return {'speech': f"{len(items)} ta vakansiya topdim, ekraningizda. Batafsil "
                          f"ma'lumot uchun qaysинини ayting.",
                'ui': ui.card_list(ss.ref, items)}

    # Aks holda: sayt vakansiyalari (bo'lsa) + tashqi manbalar birga (link_list).
    cards = [_job_link_card(j) for j in jobs]
    cards.extend(l.to_card() for l in ext_listings)
    if not cards:
        return {'speech': "Bu bo'yicha vakansiya topilmadi — saytda ham, tashqi "
                          "saytlarda ham. O'zingiz ish e'loni joylashni xohlaysizmi?"}

    n_local, n_ext = len(jobs), len(ext_listings)
    if n_local and n_ext:
        speech = (f"Saytimizda {n_local} ta, internetdan (HH, OLX) yana {n_ext} ta "
                  f"vakansiya topdim. Ekraningizda.")
    elif n_ext:
        speech = (f"Saytimizda topilmadi, lekin internetdan (HH, OLX) {n_ext} ta "
                  f"vakansiya topdim. Ekraningizda.")
    else:
        speech = f"{n_local} ta vakansiya topdim, ekraningizda."
    return {'speech': speech, 'ui': ui.link_list(cards)}


def _job_pick_item(j, i):
    """Sayt vakansiyasini card_list (TANLANADIGAN) elementiga aylantiradi."""
    from django.urls import reverse
    sub = ' · '.join(p for p in (j.company, _salary(j.salary_min, j.salary_max),
                                 j.location) if p)
    try:
        url = reverse('job_detail', args=[j.pk])
    except Exception:
        url = ''
    return {'id': f'job:{j.pk}', 'index': i, 'job_id': str(j.pk),
            'title': j.title, 'subtitle': sub or j.company, 'url': url,
            'aliases': [j.title.lower(), (j.company or '').lower()],
            'price': (j.salary_min or None),
            'phone': j.contact_phone or '', 'icon': '💼'}


def _job_link_card(j):
    """Sayt vakansiyasini link_list kartasiga aylantiradi (tashqi bilan aralashganda)."""
    from django.urls import reverse
    sub = ' · '.join(p for p in (j.company, _salary(j.salary_min, j.salary_max),
                                 j.location) if p)
    try:
        url = reverse('job_detail', args=[j.pk])
    except Exception:
        url = ''
    return {'title': j.title, 'subtitle': sub or j.company, 'url': url,
            'phone': j.contact_phone or '', 'tags': ['Bizda'], 'icon': '💼'}


# ── job_details ──────────────────────────────────────────────────────────────

@tool(
    section='jobs', action='job_details',
    description="Bitta vakansiyaning to'liq ma'lumoti (tavsif, maosh, aloqa).",
    params={'job_id': ('str', True, "search_jobs natijasidagi ID")},
)
def job_details(ctx, job_id):
    from django.core.exceptions import ValidationError
    from django.urls import reverse
    from main.models import JobAd

    jid = str(job_id).replace('job:', '').strip()
    try:
        j = JobAd.objects.filter(pk=jid, status='active').first()
    except (ValueError, ValidationError):
        j = None
    if j is None:
        return {'ok': False, 'speech': "Bunday vakansiya topilmadi."}

    sal = _salary(j.salary_min, j.salary_max) or 'Kelishilgan'
    lines = [ui.info_line('Kompaniya', j.company),
             ui.info_line('Maosh', sal),
             ui.info_line('Ish turi', _JT_LABEL.get(j.job_type, j.job_type))]
    if j.location:
        lines.append(ui.info_line('Manzil', j.location))
    if j.contact_phone:
        lines.append(ui.info_line('Telefon', j.contact_phone))
    card = {'type': 'confirm', 'title': j.title, 'lines': lines,
            'pending_id': None, 'confirm_label': '', 'cancel_label': ''}
    if j.description:
        card['note'] = j.description[:400]
    try:
        card['url'] = reverse('job_detail', args=[j.pk])
    except Exception:
        pass
    return {'speech': f"«{j.title}» — {j.company}, {sal}. Batafsili ekranda.",
            'ui': card}


# ── search_resumes ───────────────────────────────────────────────────────────

@tool(
    section='jobs', action='search_resumes',
    description="Rezyume (ish izlovchi) qidiradi — ish beruvchi xodim qidirsa.",
    params={
        'query': ('str', True, "kasb/ko'nikma, masalan «haydovchi»"),
        'experience': ('str', False, "eng kam tajriba; shu va undan yuqorilar qaytadi",
                       ['no_exp', '1_year', '1_3', '3_5', '5_plus']),
    },
)
def search_resumes(ctx, query, experience=None):
    from django.urls import reverse
    from main.models import ResumeAd

    terms = engine._search_terms(query)
    qs = ResumeAd.objects.filter(status='active')
    if terms:
        qs = qs.filter(engine._icontains_q(terms, ['title', 'skills', 'about', 'location']))
    # Tajriba filtri: so'ralgan darajа VA undan yuqorilar (>=).
    exp = _map_experience(experience)
    exp_note = ''
    if exp:
        allowed = RESUME_EXP[RESUME_EXP.index(exp):]
        qs = qs.filter(experience__in=allowed)
        exp_note = f" ({_EXP_LABEL[exp]} va undan yuqori)"
    resumes = list(qs.order_by('-created_at')[:8])
    if not resumes:
        return {'speech': "Bu bo'yicha rezyume topilmadi."}
    items = []
    for i, r in enumerate(resumes, start=1):
        sub = ' · '.join(p for p in (r.get_experience_display(),
                                     (_som(r.salary_min) + ' dan') if r.salary_min else '',
                                     r.location) if p)
        try:
            url = reverse('resume_detail', args=[r.pk])
        except Exception:
            url = ''
        items.append({'id': f'resume:{r.pk}', 'index': i, 'resume_id': str(r.pk),
                      'title': r.title, 'subtitle': sub, 'url': url,
                      'aliases': [r.title.lower()],
                      'price': (r.salary_min or None),
                      'phone': r.contact_phone or '', 'icon': '📄'})
    ss = sel.create(ctx, 'jobs', items)
    return {'speech': f"{len(items)} ta rezyume topdim{exp_note}, ekraningizda. "
                      f"Batafsil ma'lumot uchun qaysинини ayting.",
            'ui': ui.card_list(ss.ref, items)}


# ── resume_details ───────────────────────────────────────────────────────────

@tool(
    section='jobs', action='resume_details',
    description="Bitta rezyumening to'liq ma'lumoti (tajriba, ko'nikma, aloqa).",
    params={'resume_id': ('str', True, "search_resumes natijasidagi ID")},
)
def resume_details(ctx, resume_id):
    from django.core.exceptions import ValidationError
    from django.urls import reverse
    from main.models import ResumeAd

    rid = str(resume_id).replace('resume:', '').strip()
    try:
        r = ResumeAd.objects.filter(pk=rid, status='active').first()
    except (ValueError, ValidationError):
        r = None
    if r is None:
        return {'ok': False, 'speech': "Bunday rezyume topilmadi."}

    lines = [ui.info_line('Tajriba', r.get_experience_display())]
    if r.salary_min:
        lines.append(ui.info_line('Kutilayotgan maosh', _som(r.salary_min) + ' dan'))
    if r.location:
        lines.append(ui.info_line('Manzil', r.location))
    if r.skills:
        lines.append(ui.info_line("Ko'nikmalar", r.skills[:120]))
    if r.contact_phone:
        lines.append(ui.info_line('Telefon', r.contact_phone))
    card = {'type': 'confirm', 'title': r.title, 'lines': lines,
            'pending_id': None, 'confirm_label': '', 'cancel_label': ''}
    if r.about:
        card['note'] = r.about[:400]
    try:
        card['url'] = reverse('resume_detail', args=[r.pk])
    except Exception:
        pass
    return {'speech': f"«{r.title}» — {r.get_experience_display()}. Batafsili ekranda.",
            'ui': card}


# ── post_job (mutating) ──────────────────────────────────────────────────────

@tool(
    section='jobs', action='post_job',
    description="YANGI vakansiya joylaydi. Ma'lumot to'planganda chaqir.",
    params={
        'title': ('str', True, "lavozim"),
        'company': ('str', True, "kompaniya nomi"),
        'description': ('str', True, "ish tavsifi"),
        'salary_min': ('int', False, "eng kam maosh (so'm)"),
        'salary_max': ('int', False, "eng ko'p maosh (so'm)"),
        'job_type': ('str', False, "ish turi", JOB_TYPES),
        'phone': ('str', False, "aloqa telefoni"),
    },
    mutating=True,
    auth_required=True,
)
def post_job(ctx, title, company, description, salary_min=None, salary_max=None,
             job_type='full_time', phone=''):
    if job_type not in JOB_TYPES:
        job_type = 'full_time'
    phone = (phone or getattr(ctx.user, 'phone', '') or '').strip()
    sal = _salary(salary_min, salary_max)
    lines = [ui.info_line('Lavozim', title), ui.info_line('Kompaniya', company),
             ui.info_line('Ish turi', _JT_LABEL.get(job_type, job_type))]
    if sal:
        lines.append(ui.info_line('Maosh', sal))
    if phone:
        lines.append(ui.info_line('Telefon', phone))
    card = ui.confirm(None, "Vakansiyani joylashtirasizmi?", lines=lines,
                      confirm_label="Joylashtirish ✅")
    return propose('create_job',
                   payload={'title': title[:200], 'company': company[:200],
                            'description': description[:2000],
                            'salary_min': salary_min, 'salary_max': salary_max,
                            'job_type': job_type, 'phone': phone[:20]},
                   summary_card=card, amount=0,
                   speech=f"«{title}» vakansiyasини joylashtirishга tayyorman. "
                          f"Tasdiqlash uchun tugmani bosing.")


@executor('jobs', 'create_job')
def create_job(payload, user):
    from main.models import JobAd

    p = payload or {}
    if not (p.get('title') and p.get('company') and p.get('description')):
        return {'ok': False, 'reply': "Ma'lumot yetarli emas — vakansiya joylanmadi."}
    with transaction.atomic():
        job = JobAd.objects.create(
            user=user, title=p['title'][:200], company=p['company'][:200],
            description=p['description'][:2000],
            job_type=(p.get('job_type') if p.get('job_type') in JOB_TYPES else 'full_time'),
            salary_min=(p.get('salary_min') or None),
            salary_max=(p.get('salary_max') or None),
            contact_phone=(p.get('phone') or '')[:20], status='active',
        )
    return {'ok': True, 'reply': f"Vakansiya joylandi! ✅ «{job.title}» endi ko'rinadi.",
            'job_id': str(job.id)}


# ── post_resume (mutating) ───────────────────────────────────────────────────

@tool(
    section='jobs', action='post_resume',
    description="YANGI rezyume joylaydi (ish izlovchi uchun).",
    params={
        'title': ('str', True, "kasb/mavzu"),
        'about': ('str', True, "o'zi haqida qisqacha"),
        'skills': ('str', False, "ko'nikmalar"),
        'salary_min': ('int', False, "kutilayotgan eng kam maosh"),
        'phone': ('str', False, "aloqa telefoni"),
    },
    mutating=True,
    auth_required=True,
)
def post_resume(ctx, title, about, skills='', salary_min=None, phone=''):
    phone = (phone or getattr(ctx.user, 'phone', '') or '').strip()
    lines = [ui.info_line('Mavzu', title)]
    if salary_min:
        lines.append(ui.info_line('Maosh', _som(salary_min) + ' dan'))
    if phone:
        lines.append(ui.info_line('Telefon', phone))
    card = ui.confirm(None, "Rezyumeni joylashtirasizmi?", lines=lines,
                      confirm_label="Joylashtirish ✅")
    return propose('create_resume',
                   payload={'title': title[:200], 'about': about[:2000],
                            'skills': skills[:1000], 'salary_min': salary_min,
                            'phone': phone[:20]},
                   summary_card=card, amount=0,
                   speech="Rezyumeni joylashtirishга tayyorman. Tasdiqlash uchun tugmani bosing.")


@executor('jobs', 'create_resume')
def create_resume(payload, user):
    from main.models import ResumeAd

    p = payload or {}
    if not (p.get('title') and p.get('about')):
        return {'ok': False, 'reply': "Ma'lumot yetarli emas — rezyume joylanmadi."}
    with transaction.atomic():
        r = ResumeAd.objects.create(
            user=user, title=p['title'][:200], about=p['about'][:2000],
            skills=(p.get('skills') or '')[:1000],
            salary_min=(p.get('salary_min') or None),
            contact_phone=(p.get('phone') or '')[:20], status='active',
        )
    return {'ok': True, 'reply': f"Rezyume joylandi! ✅ «{r.title}».",
            'resume_id': str(r.id)}


# ── my_resumes (o'qish) — foydalanuvchining o'z rezyumelari ──────────────────

@tool(
    section='jobs', action='my_resumes',
    description="Foydalanuvchining O'Z rezyumelari («rezyumelarim»).",
    params={},
    auth_required=True,
)
def my_resumes(ctx, **_):
    from django.urls import reverse
    from main.models import ResumeAd

    resumes = list(ResumeAd.objects.filter(user=ctx.user).order_by('-created_at')[:10])
    if not resumes:
        return {'speech': "Sizда hali rezyume yo'q. Yangi rezyume joylashni "
                          "xohlaysizmi? Kasbingiz va o'zingiz haqingizda aytsangiz — "
                          "men joylab beraman."}
    li = []
    for r in resumes:
        try:
            url = reverse('resume_detail', args=[r.pk])
        except Exception:
            url = ''
        status = 'faol' if r.status == 'active' else r.status
        li.append({'title': r.title, 'subtitle': f"{status} · {r.created_at:%d-%m-%Y}",
                   'url': url, 'icon': '📄'})
    return {'speech': f"Sizда {len(li)} ta rezyume bor, ekraningizda.",
            'ui': ui.link_list(li)}


# ── my_jobs (o'qish) — foydalanuvchining o'z vakansiyalari ───────────────────

@tool(
    section='jobs', action='my_jobs',
    description="Foydalanuvchining O'Z vakansiyalari («vakansiyalarim»).",
    params={},
    auth_required=True,
)
def my_jobs(ctx, **_):
    from django.urls import reverse
    from main.models import JobAd

    jobs = list(JobAd.objects.filter(user=ctx.user).order_by('-created_at')[:10])
    if not jobs:
        return {'speech': "Sizда hali joylagan vakansiya yo'q. Yangi ish e'loni "
                          "joylashni xohlaysizmi?"}
    li = []
    for j in jobs:
        try:
            url = reverse('job_detail', args=[j.pk])
        except Exception:
            url = ''
        status = 'faol' if j.status == 'active' else j.status
        li.append({'title': j.title, 'subtitle': f"{j.company} · {status}",
                   'url': url, 'icon': '💼'})
    return {'speech': f"Siz joylagan {len(li)} ta vakansiya, ekraningizda.",
            'ui': ui.link_list(li)}
