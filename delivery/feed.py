"""
Do'kon "yangiliklar tasmasi" (StoreUpdate) yaratish va obuna bo'lgan
foydalanuvchilarga bildirishnoma yuborish uchun yagona joy.

Web (store_detail sahifasidagi "Yangiliklar") va mobil (Flutter) ikkalasi ham
shu yerda yaratilgan StoreUpdate yozuvlarini o'qiydi; bildirishnoma esa mavjud
`notifications.models.notify()` orqali yuboriladi — u DB'ga yozadi (veb
"qo'ng'iroq" belgisi) VA WebSocket guruhiga jonli push qiladi (veb + mobil
ikkalasi ham shu kanalga ulanadi), shu bilan 2.2-band talabi bittagina
chaqiruv bilan bajariladi.
"""
from django.urls import reverse

from notifications.models import notify
from .models import StoreUpdate, StoreSubscription

# "Tugadi" holati spam bo'lishi mumkin — faqat tasmada ko'rinadi, push ketmaydi.
PUSH_TYPES = {'new_product', 'price_changed', 'restocked', 'announcement'}


def _update_text(update):
    store_name = update.store.name
    product_name = update.product.name if update.product else ''
    if update.update_type == 'new_product':
        return f"«{store_name}» yangi mahsulot qo'shdi: {product_name}"
    if update.update_type == 'price_changed':
        return f"«{store_name}»da narx yangilandi: {product_name}"
    if update.update_type == 'restocked':
        return f"«{store_name}»da mahsulot qayta sotuvga qaytdi: {product_name}"
    if update.update_type == 'out_of_stock':
        return f"«{store_name}»da mahsulot tugadi: {product_name}"
    if update.update_type == 'announcement':
        return f"«{store_name}»: {update.text[:80]}"
    return f"«{store_name}»: yangilik"


def create_store_update(store, update_type, *, text='', image=None, product=None,
                        old_price=None, new_price=None):
    """StoreUpdate yozuvini yaratadi va (kerak bo'lsa) obunachilarga xabar beradi."""
    update = StoreUpdate.objects.create(
        store=store, update_type=update_type, text=text, image=image,
        product=product, old_price=old_price, new_price=new_price,
    )
    if update_type in PUSH_TYPES:
        _notify_subscribers(update)
    return update


def _notify_subscribers(update):
    store = update.store
    try:
        url = reverse('delivery:store_detail', args=[store.pk])
    except Exception:
        url = ''
    text = _update_text(update)

    subscribers = (
        StoreSubscription.objects
        .filter(store=store, is_enabled=True)
        .exclude(user_id=store.owner_id)
        .select_related('user')
    )
    for sub in subscribers:
        notify(sub.user, text, url, 'business')
