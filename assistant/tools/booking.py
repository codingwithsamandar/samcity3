"""booking bo'limi — joy bron qilish (sartaroshxona/salon/restoran). Slot-filling namuna.

Foydalanuvchi oqimi (PROMPT_7 FAZA B):
  «sartaroshxonadan joy bron qil» → qaysi sartaroshxona? → qaysi xizmat? →
  soat nechada? → to'lov naqd/oldindan? → «30 000 to'lashni tasdiqlaysizmi?» →
  tasdiq → «falon vaqtda falon sartaroshxonadan bron qildingiz».

Ko'p qadamli: har amal tanlangan ID'ni `AgentTask.slots` ga yozadi (venue_id,
service_id, staff_id, day, time). Shu tufayli oqim bir necha navbatga cho'zilsa
ham (tarix qisqarsa ham) model oldingi tanlovlarni QAYTA so'ramaydi.

⚠️ propose_booking HECH NARSA yaratmaydi — PendingAction + confirm_payment
qaytaradi. Haqiqiy VenueBooking `place_booking` (@executor) da, tasdiqdan keyin.
Mavjud booking/models mantiqi (available_slots, is_free_at) QAYTA ISHLATILADI.
"""

import re
from datetime import datetime, timedelta

from django.db import transaction

from .. import engine, selection as sel, task as task_mod, ui
from ..registry import executor, propose, tool

# Vazifa maqsadi = bo'lim nomi. ⚠️ `selection.create()` ham SelectionSet'ni
# section='booking' bo'yicha vazifaga bog'laydi — bir xil bo'lishi SHART, aks
# holda ikkita faol vazifa yaratilib, slotlar va last_ui_ref BO'LINADI.
GOAL = 'booking'
# LLM ga ko'rsatiladigan joy turlari (Venue.venue_type bilan mos).
VENUE_TYPE_ENUM = ['barber', 'beauty', 'restaurant', 'cafe', 'wedding']

# ⚠️ To'yxona (wedding) — slot emas, KUNLIK bron: sana + mehmon soni, narx
# `price_per_day`. Xizmat/usta tanlanmaydi. Shuning uchun alohida oqim
# (propose_wedding), slot oqimи (propose_booking) unga qo'llanilmaydi.
DAY_TYPES = ('wedding',)

_VT_LABEL = {'barber': 'sartaroshxona', 'beauty': 'salon', 'restaurant': 'restoran',
             'cafe': 'kafe', 'wedding': "to'yxona"}


def _som(v):
    try:
        return f"{int(v):,}".replace(',', ' ') + " so'm"
    except (TypeError, ValueError):
        return str(v)


# Karta `id` prefiksli («venue:abc») — model ba'zан xuddi shu prefiksli ID ni
# tool parametri qilib yuboradi. Prefiksни kesib, XOM pk qoldiramiz (jonli bron
# sinovда list_services aynan shu sabab error bergan edi).
_ID_PREFIXES = ('venue:', 'service:', 'staff:', 'slot:', 'booking:', 'store:', 'product:')


def _bare(val):
    s = str(val or '').strip()
    for p in _ID_PREFIXES:
        if s.startswith(p):
            return s[len(p):]
    return s


def _task(ctx):
    """Faol booking vazifasi (bo'lmasa yaratadi) — slotlar shunga yig'iladi."""
    try:
        return task_mod.get_or_create_active(ctx, goal=GOAL)
    except Exception:
        return None


def _set_slots(ctx, **kw):
    """Berilgan slotlarni faol vazifaga yozadi (None'larni tashlab)."""
    t = getattr(ctx, 'task', None) or _task(ctx)
    if t is None:
        return
    ctx.task = t
    for k, v in kw.items():
        if v is not None:
            t.set_slot(k, v)          # slots + missing ni yangilaydi (saqlamaydi)
    try:
        t.save(update_fields=['slots', 'missing', 'updated_at'])
    except Exception:
        pass


def _parse_day(day):
    """'bugun'/'ertaga'/'YYYY-MM-DD' → date. Standart — bugun.

    Substring bo'yicha ham topadi: «ertaga soat 3 da» → ertaga. Faqat vaqt
    berilsa («11 da») — kun aniqlanmaydi, standart bugun qoladi.
    """
    from django.utils import timezone
    today = timezone.localdate()
    d = (day or '').strip().lower()
    if not d:
        return today
    m = re.search(r'\d{4}-\d{2}-\d{2}', d)
    if m:
        try:
            return datetime.strptime(m.group(0), '%Y-%m-%d').date()
        except ValueError:
            pass
    if 'ertaga' in d or 'tomorrow' in d:
        return today + timedelta(days=1)
    if 'indin' in d:                      # indinga = 2 kundan keyin
        return today + timedelta(days=2)
    return today


# «11 da» → 11:00, «3 da» → 15:00 (1–8 kunduzги deb +12), «11:30» → 11:30.
_TIME_RE = re.compile(r'(\d{1,2})(?:[:.\s](\d{2}))?')


def _parse_time(s):
    """Tabiiy vaqtни 'HH:MM' ga aylantiradi. Tushunmasa None.

    «11 da»→11:00, «3 da»→15:00, «11:30»→11:30, «soat 14:30»→14:30,
    «kechqurun 7 da»→19:00. Faqat SON bo'lsa (daqiqasиz) va 1–8 oralig'ида —
    kunduzги deb +12 qilinadi (odam «3 da» deganда 15:00'ни nazarda tutadi).
    """
    if not s:
        return None
    txt = str(s).strip().lower()
    # «yarim» / «:30» kabi holatlar oddiy — asosiy raqamни olamiz
    m = _TIME_RE.search(txt)
    if not m:
        return None
    h = int(m.group(1))
    mm = int(m.group(2)) if m.group(2) is not None else 0
    explicit_min = m.group(2) is not None
    # «kechqurun/kechga»/«tunda» — kechки vaqt belgisи
    evening = any(w in txt for w in ('kech', 'tun', 'oqshom'))
    if not explicit_min and 1 <= h <= 8:
        h += 12                            # «3 da» → 15:00
    elif evening and 1 <= h <= 11:
        h += 12                            # «kechqurun 7 da» → 19:00
    if not (0 <= h <= 23 and 0 <= mm <= 59):
        return None
    return f"{h:02d}:{mm:02d}"


# ── find_venue ───────────────────────────────────────────────────────────────

@tool(
    section='booking', action='find_venue',
    description="Bron qilinadigan joyni topadi (sartaroshxona, salon, restoran). "
                "Bron oqimining birinchi qadami.",
    params={
        'query': ('str', False, "nom yoki mahsulot bo'yicha qidiruv (ixtiyoriy)"),
        'venue_type': ('str', False,
                       "joy turi: barber=sartaroshxona, beauty=salon, "
                       "restaurant=restoran, cafe=kafe", VENUE_TYPE_ENUM),
    },
)
def find_venue(ctx, query='', venue_type='barber'):
    from booking.models import Venue

    qs = Venue.objects.filter(is_active=True)
    if venue_type in VENUE_TYPE_ENUM:
        qs = qs.filter(venue_type=venue_type)
    terms = engine._search_terms(query) if query else []
    if terms:
        qs = qs.filter(engine._icontains_q(terms, ['name', 'address', 'description']))

    venues = list(qs[:10])
    if not venues:
        label = _VT_LABEL.get(venue_type, 'joy')
        return {'speech': f"Hozircha bron qilinadigan {label} topilmadi."}

    is_day = venue_type in DAY_TYPES
    _task(ctx)
    items = []
    for i, v in enumerate(venues, start=1):
        if is_day:
            # To'yxonada muhimi — sig'im va kunlik narx (xizmat/usta emas).
            parts = [f"{v.capacity} kishilik" if v.capacity else '',
                     _som(v.price_per_day) + ' / kun' if v.price_per_day else '',
                     v.address or '']
            sub = ' · '.join(p for p in parts if p)
        else:
            sub = v.address or v.get_venue_type_display()
        items.append({
            'id': f'venue:{v.pk}', 'index': i, 'title': v.name,
            'subtitle': sub,
            'aliases': [engine._norm(v.name)], 'venue_id': str(v.pk),
            'price': (v.price_per_day if is_day else None),
        })
    ss = sel.create(ctx, 'booking', items)

    # ⚠️ Bitta variant — «tanlang» demay, o'zimiz tanlaymiz va keyingi qadamга
    # o'tamiz (bitta joyни «qaysi birini?» deб so'rash g'aliz).
    if len(venues) == 1:
        v = venues[0]
        _set_slots(ctx, venue_id=str(v.pk))
        nxt = ("Qaysi kunga va necha kishiga bron qilamiz?" if is_day
               else "Qaysi xizmat kerak?")
        return {'speech': f"«{v.name}» ni topdim. {nxt}",
                'ui': ui.card_list(ss.ref, items)}
    return {'speech': f"{len(items)} ta joy topdim, ekraningizda. Qaysi biridan "
                      f"bron qilamiz?",
            'ui': ui.card_list(ss.ref, items)}


# ── list_services ────────────────────────────────────────────────────────────

@tool(
    section='booking', action='list_services',
    description="Tanlangan joyning xizmatlari va narxlari (avval find_venue).",
    params={'venue_id': ('str', True, "joy ID (find_venue natijasidan)")},
)
def list_services(ctx, venue_id):
    from booking.models import Venue

    venue_id = _bare(venue_id)
    v = Venue.objects.filter(pk=venue_id, is_active=True).first()
    if v is None:
        return {'speech': "Bunday joy topilmadi. Avval joyni qidiring."}
    _set_slots(ctx, venue_id=str(v.pk))

    services = list(v.services.filter(is_active=True))
    if not services:
        return {'speech': f"«{v.name}» uchun xizmatlar ro'yxati hozircha yo'q."}

    items = []
    for i, s in enumerate(services, start=1):
        items.append({
            'id': f'service:{s.pk}', 'index': i, 'title': s.name,
            'subtitle': f"{_som(s.price)} · {s.duration_minutes} daq",
            'aliases': [engine._norm(s.name)], 'service_id': str(s.pk),
            'price': int(s.price),
        })
    ss = sel.create(ctx, 'booking', items)

    # Bitta xizmat — avto-tanlab, vaqt so'rashga o'tamiz.
    if len(services) == 1:
        s = services[0]
        _set_slots(ctx, service_id=str(s.pk))
        return {'speech': f"«{s.name}» ({_som(s.price)}) tanlandi. Qaysi kunга va "
                          f"soat nechада yozilasiz?",
                'ui': ui.product_grid(ss.ref, items)}
    return {'speech': f"«{v.name}» xizmatlari ekraningizda. Qaysi xizmat kerak?",
            'ui': ui.product_grid(ss.ref, items)}


# ── list_staff ───────────────────────────────────────────────────────────────

@tool(
    section='booking', action='list_staff',
    description="Joyning ustalari/ishchilari (ixtiyoriy — usta tanlash uchun).",
    params={'venue_id': ('str', True, "joy ID")},
)
def list_staff(ctx, venue_id):
    from booking.models import Venue

    venue_id = _bare(venue_id)
    v = Venue.objects.filter(pk=venue_id, is_active=True).first()
    if v is None:
        return {'speech': "Bunday joy topilmadi."}
    _set_slots(ctx, venue_id=str(v.pk))

    staff = v.active_staff()
    if not staff:
        return {'speech': f"«{v.name}» da usta tanlash yo'q — istalgan bo'sh "
                          f"vaqtni tanlashingiz mumkin."}
    items = []
    for i, s in enumerate(staff, start=1):
        sub = s.specialty or 'Usta'
        if s.experience_years:
            sub += f" · {s.experience_years} yil tajriba"
        items.append({
            'id': f'staff:{s.pk}', 'index': i, 'title': s.name, 'subtitle': sub,
            'aliases': [engine._norm(s.name)], 'staff_id': str(s.pk),
        })
    ss = sel.create(ctx, 'booking', items)
    # Bitta usta — avto-tanlab, vaqtга o'tamiz.
    if len(staff) == 1:
        _set_slots(ctx, staff_id=str(staff[0].pk))
        return {'speech': f"Usta {staff[0].name}. Qaysi kunга va soat nechада "
                          f"yozilasiz?",
                'ui': ui.card_list(ss.ref, items)}
    return {'speech': f"{len(items)} ta usta bor, ekraningizda. Qaysi ustaga "
                      f"yozilasiz? (yoki «farqi yo'q» deng)",
            'ui': ui.card_list(ss.ref, items)}


# ── available_slots ──────────────────────────────────────────────────────────

@tool(
    section='booking', action='available_slots',
    description="Berilgan kun uchun bo'sh vaqtlarni ko'rsatadi (avval joy tanlanadi).",
    params={
        'venue_id': ('str', True, "joy ID"),
        'day': ('str', False, "kun: bugun / ertaga / YYYY-MM-DD (standart bugun)"),
        'service_id': ('str', False, "xizmat ID (davomiylik uchun)"),
        'staff_id': ('str', False, "usta ID (ixtiyoriy)"),
    },
)
def available_slots(ctx, venue_id, day='bugun', service_id=None, staff_id=None):
    from booking.models import Venue, VenueService, VenueStaff

    venue_id, service_id, staff_id = _bare(venue_id), \
        (_bare(service_id) if service_id else None), \
        (_bare(staff_id) if staff_id else None)
    v = Venue.objects.filter(pk=venue_id, is_active=True).first()
    if v is None:
        return {'speech': "Bunday joy topilmadi."}

    date = _parse_day(day)
    dur = 30
    if service_id:
        svc = VenueService.objects.filter(pk=service_id, venue=v).first()
        if svc:
            dur = svc.duration_minutes
    staff = VenueStaff.objects.filter(pk=staff_id, venue=v).first() if staff_id else None

    _set_slots(ctx, venue_id=str(v.pk), day=date.isoformat(),
               service_id=(str(service_id) if service_id else None),
               staff_id=(str(staff.pk) if staff else None))

    slots = v.available_slots(date, staff=staff, duration_minutes=dur)
    if not slots:
        return {'speech': f"{date:%d-%m} kuni bo'sh vaqt qolmadi. Boshqa kunni "
                          f"ayting (masalan «ertaga»)."}

    items = []
    for i, hhmm in enumerate(slots[:12], start=1):
        items.append({'id': f'slot:{hhmm}', 'index': i, 'title': hhmm,
                      'subtitle': f"{date:%d-%m}", 'aliases': [hhmm], 'time': hhmm})
    ss = sel.create(ctx, 'booking', items)
    return {'speech': f"{date:%d-%m} kuni {len(items)} ta bo'sh vaqt bor, "
                      f"ekraningizda. Soat nechada yozilasiz?",
            'ui': ui.card_list(ss.ref, items)}


# ── propose_booking (mutating=True → tasdiq) ────────────────────────────────

@tool(
    section='booking', action='propose_booking',
    description="Bronni tasdiqqa tayyorlaydi va TASDIQ kartasini ko'rsatadi. "
                "Bron faqat foydalanuvchi tasdiqlagach yaratiladi. Barcha ma'lumot "
                "([FAOL VAZIFA] slotlari) to'lganda chaqir.",
    params={
        'venue_id': ('str', True, "joy ID"),
        'service_id': ('str', True, "xizmat ID"),
        'time': ('str', True, "boshlanish vaqti (HH:MM, available_slots'dan)"),
        'day': ('str', False, "kun (standart bugun)"),
        'staff_id': ('str', False, "usta ID (ixtiyoriy)"),
        'payment_method': ('str', False, "to'lov: cash=naqd / prepay=oldindan",
                           ['cash', 'prepay']),
    },
    mutating=True,
    auth_required=True,
)
def propose_booking(ctx, venue_id, service_id, time, day='bugun',
                    staff_id=None, payment_method='cash'):
    from booking.models import Venue, VenueService, VenueStaff

    venue_id, service_id = _bare(venue_id), _bare(service_id)
    staff_id = _bare(staff_id) if staff_id else None
    v = Venue.objects.filter(pk=venue_id, is_active=True).first()
    if v is None:
        return {'ok': False, 'speech': "Bunday joy topilmadi."}
    svc = VenueService.objects.filter(pk=service_id, venue=v, is_active=True).first()
    if svc is None:
        return {'ok': False, 'speech': "Bunday xizmat topilmadi. Avval xizmatni tanlang."}
    staff = VenueStaff.objects.filter(pk=staff_id, venue=v).first() if staff_id else None

    # Kun ham, vaqt ham bitta maydonда kelishi mumkin («ertaga soat 3 da»).
    date = _parse_day(f"{day or ''} {time or ''}")
    hhmm = _parse_time(time) or _parse_time(day)
    if not hhmm:
        return {'ok': False, 'speech': "Vaqtни tushunmadim. Masalan «11 da» yoki "
                                       "«14:30» deб ayting."}

    # Vaqt haqiqatan bo'sh va ish vaqtида ekanини tekshiramiz (aks holда tasdiq
    # kartаси chiqib, tasdiqда «band» bo'lardi — noqulay).
    dur0 = int(svc.duration_minutes or 30)
    free_slots = v.available_slots(date, staff=staff, duration_minutes=dur0)
    if hhmm not in free_slots:
        if free_slots:
            taklif = ', '.join(free_slots[:5])
            return {'ok': False,
                    'speech': f"{date:%d-%m} kuni soat {hhmm} bo'sh emas. Bo'sh "
                              f"vaqtlar: {taklif}. Qaysини tanlaysiz?"}
        return {'ok': False,
                'speech': f"{date:%d-%m} kuni bo'sh vaqt qolmadi. Boshqa kunни "
                          f"ayting (masalan «ertaga»)."}
    time = hhmm

    # Oldindan to'lov majburiy bo'lsa — payment_method 'prepay'.
    if v.prepay_required:
        payment_method = 'prepay'
    amount = int(svc.price)

    when = f"{date:%d-%m} {time}"
    who = f", usta: {staff.name}" if staff else ""
    pay = "oldindan to'lov" if payment_method == 'prepay' else "joyda naqd"
    card = ui.confirm_payment(
        pending_id=None,
        lines=[ui.money_line(svc.name, amount)],
        total=amount,
        note=f"{v.name} · {when}{who} · {pay}",
    )
    speech = (f"{when} ga «{v.name}» — {svc.name}, {_som(amount)} ({pay}). "
              f"Tasdiqlash uchun tugmani bosing.")
    return propose('place_booking',
                   payload={'venue_id': str(v.pk), 'service_id': str(svc.pk),
                            'staff_id': (str(staff.pk) if staff else None),
                            'date': date.isoformat(), 'time': time.strip(),
                            'amount': amount, 'payment_method': payment_method},
                   summary_card=card, amount=amount, speech=speech)


# ── place_booking (@executor) — tasdiqdan KEYIN ─────────────────────────────

@executor('booking', 'place_booking')
def place_booking(payload, user):
    """Tasdiqlangan bronni yaratadi. Vaqt bandligini QAYTA tekshiradi (ikki
    kishi bir vaqtни tanlashi mumkin — tranzaksiya ichida qulflab tekshiramiz)."""
    from booking.models import Venue, VenueService, VenueStaff, VenueBooking

    p = payload or {}
    v = Venue.objects.filter(pk=p.get('venue_id'), is_active=True).first()
    svc = VenueService.objects.filter(pk=p.get('service_id')).first()
    if v is None or svc is None:
        return {'ok': False, 'reply': "Joy yoki xizmat topilmadi — bron yaratilmadi."}
    staff = VenueStaff.objects.filter(pk=p.get('staff_id')).first() if p.get('staff_id') else None

    try:
        date = datetime.strptime(p['date'], '%Y-%m-%d').date()
        start_t = datetime.strptime(p['time'], '%H:%M').time()
    except (KeyError, ValueError):
        return {'ok': False, 'reply': "Sana/vaqt noto'g'ri — bron yaratilmadi."}
    dur = svc.duration_minutes or 30
    end_t = (datetime.combine(date, start_t) + timedelta(minutes=dur)).time()

    with transaction.atomic():
        # Bandlik qayta tekshiruvi (usta bo'lsa usta bo'yicha, aks holda joy).
        if staff is not None:
            free = staff.is_free_at(date, start_t, dur)
        else:
            free = start_t.strftime('%H:%M') in v.available_slots(date, duration_minutes=dur)
        if not free:
            return {'ok': False, 'reply': "Afsus, bu vaqt band bo'lib qoldi. "
                                          "Boshqa vaqt tanlang."}

        booking = VenueBooking.objects.create(
            venue=v, user=user, service=svc, staff=staff,
            booking_date=date, start_time=start_t, end_time=end_t,
            guests=1, total_amount=int(svc.price), status='pending',
        )

    when = f"{date:%d-%m} soat {p['time']}"
    who = f", usta {staff.name}" if staff else ""
    return {'ok': True,
            'reply': f"Bron qabul qilindi! ✅ {when} da «{v.name}» dan "
                     f"{svc.name}{who}. Vaqtida boring.",
            'booking_id': str(booking.id), 'total': int(svc.price)}


# ═══════════════════════════════════════════════════════════════════════════
#  TO'YXONA (wedding) — KUNLIK bron: sana + mehmon soni
# ═══════════════════════════════════════════════════════════════════════════

def _day_taken(venue, date):
    """Shu kunда to'yxona band(mi) — kunlik bronда butun kun egallanadi."""
    from booking.models import VenueBooking
    return VenueBooking.objects.filter(
        venue=venue, booking_date=date,
        status__in=('pending', 'confirmed')).exists()


@tool(
    section='booking', action='propose_wedding',
    description="TO'YXONA (wedding) uchun KUNLIK bronни tasdiqqa tayyorlaydi. "
                "Slot/xizmat yo'q — sana va mehmon soni kerak. To'yxona tanlangach "
                "(find_venue venue_type='wedding') shuni chaqir.",
    params={
        'venue_id': ('str', True, "to'yxona ID (find_venue natijasidan)"),
        'day': ('str', True, "sana (masalan «ertaga», «15-avgust»)"),
        'guests': ('int', True, "mehmonlar soni"),
    },
    mutating=True,
    auth_required=True,
)
def propose_wedding(ctx, venue_id, day, guests):
    from booking.models import Venue

    v = Venue.objects.filter(pk=_bare(venue_id), is_active=True).first()
    if v is None:
        return {'ok': False, 'speech': "Bunday to'yxona topilmadi."}
    if v.venue_type not in DAY_TYPES:
        return {'ok': False, 'speech': "Bu joy kunlik bron qilinmaydi — vaqt "
                                       "tanlash kerak."}
    guests = int(guests or 0)
    if guests <= 0:
        return {'ok': False, 'speech': "Necha kishi bo'lishini ayting."}
    if v.capacity and guests > v.capacity:
        return {'ok': False,
                'speech': f"«{v.name}» sig'imi {v.capacity} kishi — {guests} kishi "
                          f"sig'maydi. Boshqa to'yxona tanlaymizmi?"}

    date = _parse_day(day)
    if _day_taken(v, date):
        return {'ok': False,
                'speech': f"{date:%d-%m} kuni «{v.name}» band. Boshqa kunни ayting."}

    amount = int(v.price_per_day or 0)
    # ⚠️ `propose(amount=...)` — guard'ning SARF limiti (single/daily). U AGENT
    # HOZIR o'tkazayotgan pulni bildiradi, ekranда ko'rsatilgan narxni emas.
    # Oldindan to'lov talab qilinmasa (odatiy to'yxona) hozir pul ko'chmaydi —
    # egasi bog'lanib, to'lov offline bo'ladi — shuning uchun guard summasi 0.
    # Prepay talab qilinsa esa haqiqiy summa beriladi va 2 mln limitidan oshsa
    # guard to'g'ri to'xtatadi («saytdan qo'lda to'lang»).
    charge_now = amount if v.prepay_required else 0
    lines = [ui.money_line(f"{v.name} — kunlik", amount)] if amount else []
    pay = "oldindan to'lov" if v.prepay_required else "to'lov joy egasi bilan"
    card = ui.confirm_payment(
        pending_id=None, lines=lines, total=amount,
        note=f"{date:%d-%m-%Y} · {guests} kishi · {pay}"
             + (f" · {v.address}" if v.address else ''),
    )
    speech = (f"{date:%d-%m} kuni «{v.name}», {guests} kishi"
              + (f", {_som(amount)}" if amount else '')
              + ". Tasdiqlash uchun tugmani bosing.")
    return propose('place_wedding',
                   payload={'venue_id': str(v.pk), 'date': date.isoformat(),
                            'guests': guests, 'amount': amount},
                   summary_card=card, amount=charge_now, speech=speech)


@executor('booking', 'place_wedding')
def place_wedding(payload, user):
    """Tasdiqlangan kunlik (to'yxona) bronни yaratadi. Kun bandligini QAYTA
    tekshiradi — ikki kishi bir kunни tanlashi mumkin."""
    from booking.models import Venue, VenueBooking

    p = payload or {}
    v = Venue.objects.filter(pk=p.get('venue_id'), is_active=True).first()
    if v is None:
        return {'ok': False, 'reply': "To'yxona topilmadi — bron yaratilmadi."}
    try:
        date = datetime.strptime(p['date'], '%Y-%m-%d').date()
    except (KeyError, ValueError):
        return {'ok': False, 'reply': "Sana noto'g'ri — bron yaratilmadi."}
    guests = int(p.get('guests') or 1)

    with transaction.atomic():
        if _day_taken(v, date):
            return {'ok': False, 'reply': "Afsus, bu kun band bo'lib qoldi. "
                                          "Boshqa kun tanlang."}
        booking = VenueBooking.objects.create(
            venue=v, user=user, service=None, staff=None,
            booking_date=date, start_time=None, end_time=None,
            guests=guests, total_amount=int(p.get('amount') or 0), status='pending',
        )
    return {'ok': True,
            'reply': f"To'yxona bron qilindi! ✅ {date:%d-%m-%Y} kuni «{v.name}», "
                     f"{guests} kishi. Joy egasi siz bilan bog'lanadi.",
            'booking_id': str(booking.id), 'total': int(p.get('amount') or 0)}


# ── my_bookings (o'qish) ─────────────────────────────────────────────────────

@tool(
    section='booking', action='my_bookings',
    description="Foydalanuvchining bronlari va ularning holatини ko'rsatadi.",
    params={},
    auth_required=True,
)
def my_bookings(ctx, **_):
    from booking.models import VenueBooking

    bookings = list(VenueBooking.objects.filter(user=ctx.user)
                    .select_related('venue', 'service').order_by('-created_at')[:6])
    if not bookings:
        return {'speech': "Sizда hali bron yo'q."}
    items, active = [], 0
    for b in bookings:
        svc = b.service.name if b.service else 'Bron'
        tm = f"{b.start_time:%H:%M}" if b.start_time else ''
        items.append({
            'id': f'booking:{b.pk}', 'index': len(items) + 1,
            'title': f"{b.venue.name} — {svc}",
            'subtitle': f"{b.booking_date:%d-%m} {tm} · {b.get_status_display()}",
            'aliases': [engine._norm(b.venue.name)], 'booking_id': str(b.pk),
        })
        if b.status in ('pending', 'confirmed'):
            active += 1
    ss = sel.create(ctx, 'booking', items)
    tail = " Bekor qilmoqchi bo'lsangiz, qaysи bronни ayting." if active else ""
    return {'speech': f"{len(items)} ta bron topdim, ekraningizda.{tail}",
            'ui': ui.card_list(ss.ref, items)}


# ── cancel_booking (mutating) ────────────────────────────────────────────────

@tool(
    section='booking', action='cancel_booking',
    description="Bronni bekor qiladi (faqat o'z broni). my_bookings'даги booking ID'sини ber.",
    params={'booking_id': ('str', True, "bron ID (my_bookings natijasidan)")},
    mutating=True,
    auth_required=True,
    owns={'booking_id': 'booking.VenueBooking'},
)
def cancel_booking(ctx, booking_id):
    from booking.models import VenueBooking

    bid = _bare(booking_id)
    b = VenueBooking.objects.filter(pk=bid, user=ctx.user).select_related('venue', 'service').first()
    if b is None:
        return {'ok': False, 'speech': "Bunday bron topilmadi."}
    if b.status not in ('pending', 'confirmed'):
        return {'ok': False, 'speech': f"Bu bronни bekor qilib bo'lmaydi "
                                       f"(holati: {b.get_status_display()})."}
    svc = b.service.name if b.service else 'Bron'
    tm = f"{b.start_time:%H:%M}" if b.start_time else ''
    card = ui.confirm(None, "Bronni bekor qilasizmi?",
                      lines=[ui.info_line('Joy', b.venue.name),
                             ui.info_line('Xizmat', svc),
                             ui.info_line('Vaqt', f"{b.booking_date:%d-%m} {tm}")],
                      confirm_label="Ha, bekor qil", cancel_label="Yo'q")
    return propose('do_cancel_booking', payload={'booking_id': str(b.pk)},
                   summary_card=card, amount=0,
                   speech=f"«{b.venue.name}» — {svc} broniни bekor qilishни "
                          f"tasdiqlaysizmi?")


@executor('booking', 'do_cancel_booking')
def do_cancel_booking(payload, user):
    from booking.models import VenueBooking

    b = VenueBooking.objects.filter(pk=(payload or {}).get('booking_id'), user=user).first()
    if b is None:
        return {'ok': False, 'reply': "Bron topilmadi."}
    if b.status not in ('pending', 'confirmed'):
        return {'ok': False, 'reply': "Bu bron allaqachon yakunlangan yoki bekor qilingan."}
    with transaction.atomic():
        b.status = 'cancelled'
        b.save(update_fields=['status'])
    return {'ok': True, 'reply': f"Bron bekor qilindi. «{b.venue.name}» — "
                                 f"{b.booking_date:%d-%m}. 👍"}
