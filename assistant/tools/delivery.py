"""delivery bo'limi — do'kon, mahsulot, savat, BUYURTMA. Yozish + tasdiq namunasi.

To'rt amal butun agent naqshini ko'rsatadi:
  find_store    — o'qish (card_list + SelectionSet)
  list_products — o'qish (product_grid + SelectionSet)
  cart_add      — yozish, PULSIZ (mutating=False) — savatga qo'shadi
  propose_order — PUL KETADI (mutating=True) → PendingAction + confirm_payment

⚠️ propose_order HECH NARSA yaratmaydi — u faqat «nima qilinishi kerak»ligini
tasvirlaydi. Haqiqiy buyurtma `place_order` (@executor) da, foydalanuvchi
tasdiqlagach yaratiladi. Bu naqsh delivery.views.checkout mantiqini takrorlaydi
(stock qulflash, do'kon bo'yicha bo'lish, CheckoutGroup) — lekin chatga karta
ma'lumoti KIRITILMAYDI: yetkazib beruvchi do'konlar uchun «yetkazishda naqd».
"""

from django.db import transaction
from django.db.models import Q

from .. import engine, selection as sel, ui
from ..registry import executor, propose, tool


def _som(v):
    try:
        return f"{int(v):,}".replace(',', ' ') + " so'm"
    except (TypeError, ValueError):
        return str(v)


def _delivery_fee():
    """Yetkazish narxi — delivery.views dagi yagona manbadan (dublikat qilmaymiz)."""
    from delivery.views import DELIVERY_FEE
    return DELIVERY_FEE


# ── find_store ───────────────────────────────────────────────────────────────

@tool(
    section='delivery', action='find_store',
    description="Do'kon qidiradi (nomi yoki mahsuloti bo'yicha) — buyurtmaning "
                "1-qadami.",
    params={'query': ('str', True, "do'kon nomi yoki mahsulot, masalan «lavash»")},
)
def find_store(ctx, query):
    from delivery.models import Store

    terms = engine._search_terms(query)
    qs = Store.objects.filter(is_active=True, store_type='delivery')
    if terms:
        name_q = engine._icontains_q(terms, ['name', 'description', 'address'])
        prod_q = Q()
        for t in terms:
            prod_q |= Q(products__name__icontains=t)
        qs = qs.filter(name_q | prod_q).distinct()

    stores = list(qs[:20])
    # Joylashuv bo'lsa — masofa bo'yicha tartiblaymiz.
    loc = getattr(ctx, 'location', None)
    have_loc = (isinstance(loc, (tuple, list)) and len(loc) == 2 and loc[0] is not None)
    if have_loc:
        def _dist(s):
            if s.latitude is None or s.longitude is None:
                return 1e9
            return engine._haversine(loc[0], loc[1], s.latitude, s.longitude)
        stores.sort(key=_dist)
    stores = stores[:10]

    if not stores:
        return {'speech': "Bu bo'yicha do'kon topolmadim. Boshqacharoq qidirib "
                          "ko'ring yoki «barcha do'konlar»ni ochaman."}

    items = []
    for i, s in enumerate(stores, start=1):
        sub = s.address or "Do'kon"
        dist_km = None
        if have_loc and s.latitude is not None and s.longitude is not None:
            dist_km = round(engine._haversine(loc[0], loc[1], s.latitude, s.longitude), 3)
            sub = f"{engine._fmt_dist(dist_km)} · {sub}"
        items.append({
            'id': f'store:{s.pk}', 'index': i, 'title': s.name, 'subtitle': sub,
            'aliases': [engine._norm(s.name)], 'store_id': s.pk, 'distance': dist_km,
        })

    ss = sel.create(ctx, 'delivery', items)
    speech = (f"{len(items)} ta do'kon topdim, ekraningizda ko'rsatdim. "
              f"Qaysi biridan olasiz?")
    return {'speech': speech, 'ui': ui.card_list(ss.ref, items)}


# ── list_products ────────────────────────────────────────────────────────────

@tool(
    section='delivery', action='list_products',
    description="Tanlangan do'kon mahsulotlari (avval find_store).",
    params={'store_id': ('int', True, "do'kon ID (find_store natijasidan)")},
)
def list_products(ctx, store_id):
    from delivery.models import Store

    store = Store.objects.filter(pk=store_id, is_active=True).first()
    if store is None:
        return {'speech': "Bunday do'kon topilmadi. Avval do'konni qidiring."}

    prods = list(store.products.filter(is_available=True)[:24])
    if not prods:
        return {'speech': f"«{store.name}» do'konida hozircha mahsulot yo'q."}

    items = []
    for i, p in enumerate(prods, start=1):
        items.append({
            'id': f'product:{p.pk}', 'index': i, 'title': p.name,
            'subtitle': _som(p.price),
            'aliases': [engine._norm(p.name)],
            'product_id': p.pk, 'price': float(p.price),
            'image': p.cover_image_url or '',
        })

    ss = sel.create(ctx, 'delivery', items)
    speech = (f"«{store.name}» do'konida {len(items)} ta mahsulot bor, "
              f"ekraningizda. Qaysi birini savatga qo'shay?")
    return {'speech': speech, 'ui': ui.product_grid(ss.ref, items, store_id=store.pk)}


# ── cart_add (yozish, pulsiz) ────────────────────────────────────────────────

@tool(
    section='delivery', action='cart_add',
    description="Mahsulotni savatga qo'shadi. ALBATTA chaqir — «qo'shdim» deyishning "
                "o'zi yetarli emas.",
    params={
        'product_id': ('int', True, "mahsulot ID (list_products'dan)"),
        'qty': ('int', False, "soni, standart 1"),
    },
    mutating=False,        # savatga qo'shish — pul ketmaydi
    auth_required=True,
)
def cart_add(ctx, product_id, qty=1):
    from delivery.models import Product, CartItem, get_active_cart

    p = Product.objects.filter(pk=product_id, is_available=True).first()
    if p is None:
        return {'ok': False, 'speech': "Bu mahsulot topilmadi yoki sotuvda yo'q."}
    qty = max(1, min(99, int(qty or 1)))
    if p.stock is not None and qty > p.stock:
        return {'ok': False,
                'speech': f"«{p.name}» uchun omborda {p.stock} dona bor, shuncha qo'sha olaman."}

    cart = get_active_cart(ctx.user)
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=p, defaults={'quantity': qty})
    if not created:
        item.quantity = min(99, item.quantity + qty)
        item.save(update_fields=['quantity'])

    return {'speech': f"«{p.name}» savatga qo'shildi (jami {item.quantity} dona). "
                      f"Yana biror narsa qo'shamizmi yoki buyurtma qilamizmi?"}


# ── propose_order (mutating=True → tasdiq) ───────────────────────────────────

# Manzilsiz buyurtma kuryerga BO'SH manzil bilan tushadi — shuning uchun
# `address` MAJBURIY parametr va bu yerda alohida tekshiriladi.
ADDRESS_MIN_LEN = 5


def _clean_address(value):
    """Manzilni tozalaydi; yaroqsiz bo'lsa None qaytaradi.

    LLM ba'zan «manzil», «uyim», «-» kabi to'ldiruvchi matn yuboradi — bular
    kuryer uchun foydasiz, shuning uchun rad etiladi.
    """
    a = ' '.join((value or '').split())
    if len(a) < ADDRESS_MIN_LEN:
        return None
    if engine._norm(a) in ('manzil', 'uyim', 'uy', 'yo q', 'yoq', 'bilmayman'):
        return None
    return a[:300]


@tool(
    section='delivery', action='propose_order',
    description="Savatni buyurtmaga tayyorlaydi; buyurtma faqat foydalanuvchi "
                "tasdiqlagach yaratiladi. MANZIL MAJBURIY — aytilmagan bo'lsa "
                "avval so'ra, o'zingdan to'qib chiqarma.",
    params={
        'address': ('str', True, "yetkazish manzili (foydalanuvchi aytgani; "
                                 "taxmin qilma)"),
        'note': ('str', False, "kuryerga izoh"),
    },
    mutating=True,         # PUL KETADI: server majburan PendingAction qiladi
    auth_required=True,
)
def propose_order(ctx, address='', note=''):
    from delivery.models import get_active_cart

    addr = _clean_address(address)
    if addr is None:
        # Xato emas — savol. Agent shu matnni foydalanuvchiga aytadi va
        # javobini olgach propose_order'ni qaytadan chaqiradi.
        return {'ok': False,
                'speech': "Buyurtmani rasmiylashtirish uchun yetkazish manzilini "
                          "ayting — ko'cha, uy raqami va mo'ljal bo'lsa yaxshi "
                          "bo'lardi. Manzilsiz kuryer sizni topa olmaydi."}

    cart = get_active_cart(ctx.user)
    items = [it for it in cart.items.select_related('product__store')
             if _orderable(it)]
    if not items:
        return {'ok': False,
                'speech': "Savatingizda buyurtma qilsa bo'ladigan mahsulot yo'q. "
                          "Avval do'kondan mahsulot qo'shing."}

    subtotal = int(sum(it.product.price * it.quantity for it in items))
    store_count = len({it.product.store_id for it in items})
    fee = _delivery_fee() * store_count
    total = subtotal + fee

    # Manzil tasdiq kartasida KO'RINSIN — foydalanuvchi tugmani bosishdan oldin
    # noto'g'ri manzilni tuzatib olishi kerak.
    card = ui.confirm_payment(
        pending_id=None,
        lines=[ui.money_line('Mahsulotlar', subtotal),
               ui.money_line('Yetkazish', fee)],
        total=total,
        note=f"📍 {addr}" + (f" · {note}" if note else ''),
    )
    speech = (f"Jami {_som(total)} ({_som(subtotal)} + yetkazish {_som(fee)}). "
              f"Manzil: {addr}. To'g'ri bo'lsa tasdiqlash tugmasini bosing.")
    return propose('place_order',
                   payload={'address': addr, 'note': note or ''},
                   summary_card=card, amount=total, speech=speech)


def _orderable(item):
    """Chat orqali buyurtma qilsa bo'ladimi — yetkazib beruvchi (naqd) do'kon.

    Pickup (olib ketish) do'konlari oldindan KARTA to'lovini talab qiladi; chatga
    karta kiritilmaydi, shuning uchun ular bu oqimdan chiqariladi.
    """
    p = item.product
    return (p.is_available and p.store.store_type == 'delivery'
            and not p.store.pickup_enabled)


# ── place_order (@executor) — tasdiqdan KEYIN bajariladi ─────────────────────

@executor('delivery', 'place_order')
def place_order(payload, user):
    """Tasdiqlangan buyurtmani yaratadi. delivery.views.checkout naqshi bilan bir xil:
    stock qulflash, do'kon bo'yicha bo'lish, CheckoutGroup. To'lov: yetkazishda naqd.
    """
    from delivery.models import (CheckoutGroup, Order, OrderItem, Product,
                                 get_active_cart)

    note = (payload or {}).get('note', '') or ''
    # Manzilni QAYTA tekshiramiz: PendingAction payload'i propose_order'da
    # yaratilgan, lekin executor buyurtmani haqiqatda yaratadigan yagona joy —
    # bo'sh manzilli buyurtma kuryerga tushib qolmasligi shu yerda kafolatlanadi.
    addr = _clean_address((payload or {}).get('address', ''))
    if addr is None:
        return {'ok': False,
                'reply': "Yetkazish manzili ko'rsatilmagan — buyurtma yaratilmadi. "
                         "Manzilni ayting va qaytadan tasdiqlang."}
    cart = get_active_cart(user)
    items = [it for it in cart.items.select_related('product__store') if _orderable(it)]
    if not items:
        return {'ok': False, 'reply': "Savat bo'sh — buyurtma yaratilmadi."}

    fee_each = _delivery_fee()
    created = []
    with transaction.atomic():
        pids = [it.product_id for it in items]
        locked = {p.pk: p for p in
                  Product.objects.select_for_update().filter(pk__in=pids)}
        # Avval hammasini tekshiramiz (oversell himoyasi).
        for it in items:
            p = locked.get(it.product_id)
            if p is None or not p.is_available:
                return {'ok': False, 'reply': "Ayrim mahsulotlar sotuvda yo'q. "
                                              "Savatni yangilab, qaytadan urinib ko'ring."}
            if p.stock is not None and it.quantity > p.stock:
                return {'ok': False,
                        'reply': f"«{p.name}» uchun omborda {p.stock} dona qoldi."}

        groups = {}
        for it in items:
            groups.setdefault(locked[it.product_id].store_id, []).append(
                (it, locked[it.product_id]))

        cg = CheckoutGroup.objects.create(user=user)
        for _store_id, group in groups.items():
            g_sub = int(sum(p.price * it.quantity for it, p in group))
            order = Order.objects.create(
                user=user, group=cg,
                full_name=(getattr(user, 'name', '') or ''),
                phone=(getattr(user, 'phone', '') or ''),
                address=addr, note=note,
                subtotal=g_sub, delivery_fee=fee_each, total=g_sub + fee_each,
                status='pending', payment_method='cash', payment_status='unpaid',
                fulfillment_type='delivery',
            )
            for it, p in group:
                OrderItem.objects.create(
                    order=order, product=p, product_name=p.name,
                    store_name=p.store.name, price=p.price, quantity=it.quantity)
                p.stock = max(0, (p.stock or 0) - it.quantity)
                p.save(update_fields=['stock'])
            created.append(order)

        cart.items.filter(pk__in=[it.pk for it in items]).delete()

    # Do'kon egalariga bildirishnoma (best-effort — buyurtmaga ta'sir qilmaydi).
    try:
        from django.urls import reverse
        from notifications.models import notify
        url = reverse('delivery:store_orders')
        notified = set()
        for it in items:
            owner = it.product.store.owner
            if owner.id != user.id and owner.id not in notified:
                notify(owner, "Yangi buyurtma keldi 🧾", url, 'order')
                notified.add(owner.id)
    except Exception:
        pass

    n = len(created)
    total = sum(o.total for o in created)
    return {'ok': True,
            'reply': f"{n} ta do'kondan buyurtma qabul qilindi! ✅ Jami {_som(total)}, "
                     f"yetkazishda naqd. Kuryer tez orada bog'lanadi.",
            'order_ids': [str(o.id) for o in created], 'total': int(total)}


# ── view_cart (o'qish) ───────────────────────────────────────────────────────

@tool(
    section='delivery', action='view_cart',
    description="Savatdagi mahsulotlar va jami summa.",
    params={},
    auth_required=True,
)
def view_cart(ctx, **_):
    from delivery.models import get_active_cart

    cart = get_active_cart(ctx.user)
    items = list(cart.items.select_related('product'))
    if not items:
        return {'speech': "Savatingiz bo'sh. Biror do'kondan mahsulot qidiraylikmi?"}
    li = []
    for it in items:
        line = int(it.product.price * it.quantity)
        li.append({'title': f"{it.product.name} × {it.quantity}",
                   'subtitle': _som(line), 'icon': '🛒'})
    total = int(cart.get_subtotal())
    return {'speech': f"Savatда {len(items)} xil mahsulot, jami {_som(total)}. "
                      f"Buyurtma qilamizmi yoki biror narsani olib tashlaymizmi?",
            'ui': ui.link_list(li)}


# ── remove_from_cart (yozish, pulsiz) ────────────────────────────────────────

@tool(
    section='delivery', action='remove_from_cart',
    description="Savatdan bitta mahsulotni olib tashlaydi.",
    params={'product_id': ('int', True, "mahsulot ID")},
    mutating=False,
    auth_required=True,
)
def remove_from_cart(ctx, product_id):
    from delivery.models import get_active_cart

    cart = get_active_cart(ctx.user)
    item = cart.items.filter(product_id=product_id).first()
    if item is None:
        return {'ok': False, 'speech': "Bu mahsulot savatда yo'q."}
    name = item.product.name
    item.delete()
    remaining = cart.items.count()
    tail = "Savat endi bo'sh." if remaining == 0 else f"Savatда yana {remaining} xil bor."
    return {'speech': f"«{name}» savatдан olib tashlandi. {tail}"}


# ── clear_cart (yozish, pulsiz) ──────────────────────────────────────────────

@tool(
    section='delivery', action='clear_cart',
    description="Savatni butunlay bo'shatadi.",
    params={},
    mutating=False,        # pul ketmaydi — o'z savatini tozalash
    auth_required=True,
)
def clear_cart(ctx, **_):
    from delivery.models import get_active_cart

    cart = get_active_cart(ctx.user)
    n = cart.items.count()
    if n == 0:
        return {'speech': "Savatingiz allaqachon bo'sh. 🙂"}
    cart.items.all().delete()
    return {'speech': f"Savat tozalandi — {n} xil mahsulot olib tashlandi. ✅ "
                      f"Yangi buyurtма uchun biror do'kondan mahsulot qidiraylikmi?"}


# ── my_orders (o'qish) ───────────────────────────────────────────────────────

@tool(
    section='delivery', action='my_orders',
    description="Foydalanuvchining oxirgi buyurtmalari va holati.",
    params={},
    auth_required=True,
)
def my_orders(ctx, **_):
    from delivery.models import Order

    orders = list(Order.objects.filter(user=ctx.user).order_by('-created_at')[:5])
    if not orders:
        return {'speech': "Sizда hali buyurtma yo'q."}
    from django.urls import reverse
    li = []
    for o in orders:
        try:
            url = reverse('delivery:order_detail', args=[o.pk])
        except Exception:
            url = ''
        li.append({'title': f"Buyurtma · {_som(o.total)}",
                   'subtitle': f"{o.get_status_display()} · {o.created_at:%d-%m %H:%M}",
                   'url': url, 'icon': '🧾'})
    return {'speech': f"Oxirgi {len(orders)} ta buyurtmangiz, ekraningizda.",
            'ui': ui.link_list(li)}
