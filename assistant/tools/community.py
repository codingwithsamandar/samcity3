"""community bo'limi — mahalla xizmatlari: e'lonlar, murojaat, so'rovnoma.

  announcements   — mahalla + tuman rasmiy e'lonlari (o'qish)
  submit_request  — fuqaro murojaati/shikoyati (mutating → confirm → CitizenRequest)
  list_polls      — ochiq so'rovnomalar + variantlar (o'qish)
  vote            — so'rovnomaga ovoz berish (mutating → confirm → PollVote)

Tuman/mahalla `ctx.user.neighborhood` dan olinadi — LLM'dan EMAS.
"""

from django.db import transaction

from .. import selection as sel, ui
from ..registry import executor, propose, tool

# CitizenRequest.CATEGORY_CHOICES kalitlari.
REQUEST_CATEGORIES = ['road', 'water', 'electricity', 'cleaning', 'gas',
                      'lighting', 'landscaping', 'other']
_RC_LABEL = {'road': "Yo'l", 'water': 'Suv', 'electricity': 'Svet / elektr',
             'cleaning': 'Tozalik', 'gas': 'Gaz', 'lighting': "Ko'cha yoritilishi",
             'landscaping': 'Obodonlashtirish', 'other': 'Boshqa'}


def _neighborhood(ctx):
    try:
        return getattr(ctx.user, 'neighborhood', None)
    except Exception:
        return None


# ── announcements ────────────────────────────────────────────────────────────

@tool(
    section='community', action='announcements',
    description="Mahalla/tuman rasmiy e'lonlari (suv o'chishi, yig'ilish va h.k.).",
    params={},
    auth_required=True,
)
def announcements(ctx, **_):
    from main.models import DistrictAnnouncement, NeighborhoodAnnouncement

    nb = _neighborhood(ctx)
    if nb is None:
        return {'speech': "Sizда mahalla tanlanmagan. Profilда mahallangizни "
                          "tanlasangiz, mahalla e'lonlarини ko'rsataman."}

    items = []
    for a in NeighborhoodAnnouncement.objects.filter(neighborhood=nb)[:5]:
        items.append({'title': a.title, 'subtitle': f"🏘️ {nb.name} · {a.created_at:%d-%m}",
                      'icon': '📢'})
    district = getattr(nb, 'district', None)
    if district is not None:
        for a in DistrictAnnouncement.objects.filter(district=district)[:5]:
            items.append({'title': a.title,
                          'subtitle': f"🏛️ {district.name} · {a.created_at:%d-%m}",
                          'icon': '📣'})
    if not items:
        return {'speech': f"«{nb.name}» uchun hozircha rasmiy e'lon yo'q."}
    return {'speech': f"{len(items)} ta e'lon bor, ekraningizda.",
            'ui': ui.link_list(items)}


# ── submit_request (mutating) ────────────────────────────────────────────────

@tool(
    section='community', action='submit_request',
    description="Fuqaro murojaatini mahalla raisiga yuboradi (yo'l, suv, svet, "
                "tozalik). Ma'lumot to'planganda chaqir.",
    params={
        'category': ('str', True, "muammo turi", REQUEST_CATEGORIES),
        'title': ('str', True, "mavzu (qisqa)"),
        'text': ('str', True, "murojaat matni"),
    },
    mutating=True,
    auth_required=True,
)
def submit_request(ctx, category, title, text):
    if category not in REQUEST_CATEGORIES:
        category = 'other'
    nb = _neighborhood(ctx)
    lines = [ui.info_line('Muammo', _RC_LABEL.get(category, category)),
             ui.info_line('Mavzu', title)]
    if nb is not None:
        lines.append(ui.info_line('Mahalla', nb.name))
    card = ui.confirm(None, "Murojaatni yuborasizmi?", lines=lines,
                      note=text[:160], confirm_label="Yuborish ✅")
    return propose('create_request',
                   payload={'category': category, 'title': title[:200],
                            'text': text[:2000],
                            'neighborhood_id': (nb.pk if nb is not None else None)},
                   summary_card=card, amount=0,
                   speech="Murojaatingizни raisga yuborishга tayyorman. Tasdiqlash "
                          "uchun tugmani bosing.")


@executor('community', 'create_request')
def create_request(payload, user):
    from main.models import CitizenRequest, Neighborhood

    p = payload or {}
    if not (p.get('title') and p.get('text')):
        return {'ok': False, 'reply': "Ma'lumot yetarli emas — murojaat yuborilmadi."}
    nb = None
    if p.get('neighborhood_id'):
        nb = Neighborhood.objects.filter(pk=p['neighborhood_id']).first()
    with transaction.atomic():
        req = CitizenRequest.objects.create(
            user=user, neighborhood=nb,
            category=(p.get('category') if p.get('category') in REQUEST_CATEGORIES else 'other'),
            title=p['title'][:200], text=p['text'][:2000], status='submitted',
        )
    return {'ok': True,
            'reply': "Murojaatingiz yuborildi! ✅ Mahalla raisi ko'rib chiqadi. "
                     "Javobни profil → murojaatlarим bo'limidан kuzatasiz.",
            'request_id': str(req.id)}


# ── list_polls ───────────────────────────────────────────────────────────────

@tool(
    section='community', action='list_polls',
    description="Ochiq so'rovnomalar va variantlari.",
    params={},
    auth_required=True,
)
def list_polls(ctx, **_):
    from main.models import Poll

    nb = _neighborhood(ctx)
    qs = Poll.objects.filter(is_active=True)
    if nb is not None:
        from django.db.models import Q
        qs = qs.filter(Q(neighborhood=nb) | Q(neighborhood__isnull=True))
    else:
        qs = qs.filter(neighborhood__isnull=True)

    polls = [p for p in qs[:10] if p.is_open]
    if not polls:
        return {'speech': "Hozircha ochiq so'rovnoma yo'q."}

    # Variantlarни tanlash uchun SelectionSet — «A variantiga ovoz ber» yechiladi.
    items = []
    idx = 0
    lines = []
    for p in polls:
        lines.append(f"❓ {p.question}")
        for opt in p.options.all():
            idx += 1
            items.append({'id': f'polloption:{opt.pk}', 'index': idx,
                          'title': opt.text, 'subtitle': f"{p.question[:40]}",
                          'aliases': [opt.text.lower()],
                          'poll_option_id': str(opt.pk),
                          'votes': opt.vote_count()})
            lines.append(f"   {idx}) {opt.text} — {opt.vote_count()} ovoz")
    ss = sel.create(ctx, 'community', items)
    return {'speech': f"{len(polls)} ta ochiq so'rovnoma bor. Ovoz berish uchun "
                      f"variantни ayting (masalan «birinchisiga ovoz ber»).",
            'ui': ui.card_list(ss.ref, items)}


# ── vote (mutating) ──────────────────────────────────────────────────────────

@tool(
    section='community', action='vote',
    description="So'rovnomaga ovoz beradi.",
    params={'poll_option_id': ('str', True, "list_polls natijasidagi variant ID")},
    mutating=True,
    auth_required=True,
)
def vote(ctx, poll_option_id):
    from main.models import PollOption

    from django.core.exceptions import ValidationError
    oid = str(poll_option_id).replace('polloption:', '').strip()
    try:
        opt = PollOption.objects.filter(pk=oid).select_related('poll').first()
    except (ValueError, ValidationError):
        opt = None
    if opt is None:
        return {'ok': False, 'speech': "Bunday variant topilmadi. Avval "
                                       "so'rovnomalarни ko'ring."}
    if not opt.poll.is_open:
        return {'ok': False, 'speech': "Bu so'rovnoma yopilgan — ovoz berib bo'lmaydi."}
    card = ui.confirm(None, "Ovoz berasizmi?",
                      lines=[ui.info_line('So\'rovnoma', opt.poll.question[:60]),
                             ui.info_line('Variant', opt.text)],
                      confirm_label="Ovoz berish ✅")
    return propose('cast_vote', payload={'option_id': str(opt.pk)},
                   summary_card=card, amount=0,
                   speech=f"«{opt.text}» ga ovoz berishга tayyorman. Tasdiqlang.")


@executor('community', 'cast_vote')
def cast_vote(payload, user):
    from main.models import PollOption, PollVote

    p = payload or {}
    opt = PollOption.objects.filter(pk=p.get('option_id')).select_related('poll').first()
    if opt is None:
        return {'ok': False, 'reply': "Variant topilmadi — ovoz berilmadi."}
    if not opt.poll.is_open:
        return {'ok': False, 'reply': "So'rovnoma yopilgan — ovoz berilmadi."}
    with transaction.atomic():
        # single-type: eski ovozни olib tashlaymiz (bir variant); keyin yozamiz.
        if opt.poll.poll_type == 'single':
            PollVote.objects.filter(option__poll=opt.poll, user=user).delete()
        PollVote.objects.get_or_create(option=opt, user=user)
    return {'ok': True, 'reply': f"Ovozingiz qabul qilindi! ✅ «{opt.text}».",
            'poll_id': str(opt.poll.pk)}
