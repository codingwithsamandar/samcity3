"""UI direktivalari — AI javobining EKRAN qismini quradi.

Har bir tool javobi ikki qismdan iborat:
  speech — AI ovoz bilan aytadigan QISQA matn
  ui     — ekranda ko'rsatiladigan BOY tuzilma (kartalar, tasdiq, forma…)

⚠️ QOIDA: `speech` va `ui` bir-birini TAKRORLAMAYDI. AI 10 ta do'konni ovozda
sanamaydi (40 soniya) — «10 ta topdim, ekraningizda» deydi, batafsili kartalarda.

0-to'lqinda: card_list · product_grid · confirm_payment · text yetarli.
Boshqalari (live_map, order_status, form, date_picker) keyingi to'lqinlarda.
"""


def card_list(ref, items, select_mode='single', ai_can_pick=True):
    """Tanlanadigan kartalar ro'yxati (do'kon, joy). `ref` — SelectionSet kaliti.

    items — selection.py kutadigan shakl: [{id, index, title, subtitle, image?,
    aliases?, price?, distance?, rating?}, ...].
    """
    return {
        'type': 'card_list',
        'ref': ref,
        'select_mode': select_mode,     # single | multi
        'ai_can_pick': bool(ai_can_pick),
        'items': items or [],
    }


def product_grid(ref, items, store_id=None, select_mode='single'):
    """Mahsulotlar to'ri (rasm + narx). Savatga qo'shish uchun."""
    grid = {
        'type': 'product_grid',
        'ref': ref,
        'select_mode': select_mode,
        'items': items or [],
    }
    if store_id is not None:
        grid['store_id'] = store_id
    return grid


def cart_summary(items, subtotal, delivery_fee=0, total=None):
    """Savat holati — checkout'dan oldingi ko'rinish."""
    if total is None:
        total = int(subtotal) + int(delivery_fee)
    return {
        'type': 'cart_summary',
        'items': items or [],
        'subtotal': int(subtotal),
        'delivery_fee': int(delivery_fee),
        'total': int(total),
    }


def confirm_payment(pending_id, lines, total, action_url=None, cancel_url=None,
                    note=''):
    """Tasdiq kartasi — foydalanuvchi «Tasdiqlash» tugmasini bosadi.

    `lines` — [{label, amount}] ko'rinishida ajratmalar (masalan mahsulot + yetkazish).
    `action_url` — POST qilinadigan tasdiq havolasi (views /ai/confirm/<uuid>/).
    """
    card = {
        'type': 'confirm_payment',
        'pending_id': str(pending_id) if pending_id else None,
        'lines': lines or [],
        'total': int(total),
        'confirm_label': 'Tasdiqlash ✅',
        'cancel_label': 'Bekor qilish',
    }
    if action_url:
        card['action_url'] = action_url
    if cancel_url:
        card['cancel_url'] = cancel_url
    if note:
        card['note'] = note
    return card


def link_list(items):
    """MA'LUMOT ro'yxati — havolali kartalar (e'lon, ish, taksist). TANLANMAYDI.

    card_list/product_grid tanlanadi (ko'p qadamli oqim); bu esa oxirgi natija:
    foydalanuvchi bosib batafsil ko'radi yoki qo'ng'iroq qiladi.
    items — [{title, subtitle, url?, phone?, tags?: [str], icon?}]
    """
    return {'type': 'link_list', 'items': items or []}


def confirm(pending_id, title, lines=None, note='',
            confirm_label='Tasdiqlash ✅', cancel_label='Bekor qilish'):
    """PULSIZ tasdiq kartasi — e'lon joylash, murojaat yuborish, taksi chaqirish.

    `confirm_payment` narx-taqsimotli; bu esa umumiy «shuni bajaraymi?» tasdig'i.
    `lines` — [{label, value}] ko'rinishida ma'lumot qatorlari (narx emas — matn).
    action_url/cancel_url ni registry._to_pending pending_id bilan to'ldiradi.
    """
    card = {
        'type': 'confirm',
        'pending_id': str(pending_id) if pending_id else None,
        'title': title,
        'lines': lines or [],
        'confirm_label': confirm_label,
        'cancel_label': cancel_label,
    }
    if note:
        card['note'] = note
    return card


def info_line(label, value):
    """confirm.lines uchun matn qatori (label: value)."""
    return {'label': label, 'value': str(value)}


def text(body=''):
    """Oddiy matn (kartasiz javob)."""
    return {'type': 'text', 'body': body}


def money_line(label, amount):
    """confirm_payment.lines uchun bitta qator quruvchi."""
    return {'label': label, 'amount': int(amount)}
