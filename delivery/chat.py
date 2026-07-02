"""
Do'kon xodimi bilan chat — umumiy yordamchi funksiyalar.

Web, REST API va WebSocket consumer — uchalasi ham shu yerdagi funksiyalardan
foydalanadi (xabar yaratish + jonli broadcast + bildirishnoma bitta joyda).

Ishtirokchilar: thread.customer (mijoz) va thread.store.owner (do'kon egasi).
TODO (keyingi bosqich): ko'p xodimli do'kon — hozircha faqat egasi javob beradi.
"""
from django.urls import reverse

from notifications.models import notify
from .models import Store, StoreChatThread, StoreChatMessage
from .realtime import push_chat_message


def get_or_create_thread(store, customer):
    """Mijoz-do'kon juftligi uchun bitta thread (get_or_create)."""
    thread, _ = StoreChatThread.objects.get_or_create(store=store, customer=customer)
    return thread


def is_participant(thread, user):
    """Foydalanuvchi shu thread ishtirokchisi (mijoz yoki do'kon egasi)mi?"""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    return user.id == thread.customer_id or user.id == thread.store.owner_id


def create_message(thread, sender, text):
    """Xabarni yaratadi, jonli yuboradi va qabul qiluvchiga bildirishnoma beradi.

    Bildirishnoma mavjud `notify()` orqali — u DB'ga yozadi (chat oynasi yopiq
    bo'lsa "qo'ng'iroq"da ko'rinadi) VA foydalanuvchining WebSocket guruhiga
    push qiladi (2-qismdagi kanal mantig'iga mos).
    """
    text = (text or '').strip()
    if not text:
        return None
    message = StoreChatMessage.objects.create(thread=thread, sender=sender, text=text)
    # Thread'ni "eng so'nggi faollik" bo'yicha tepaga chiqarish uchun updated_at ni yangilaymiz.
    thread.save(update_fields=['updated_at'])
    push_chat_message(message)
    _notify_recipient(thread, sender, message)
    return message


def _notify_recipient(thread, sender, message):
    # Yuboruvchi mijoz bo'lsa — do'kon egasiga, aks holda mijozga xabar beramiz.
    if sender.id == thread.customer_id:
        recipient = thread.store.owner
        title = f"«{thread.store.name}» do'koniga yangi savol 💬"
    else:
        recipient = thread.customer
        title = f"«{thread.store.name}» javob berdi 💬"
    if recipient.id == sender.id:
        return
    try:
        url = reverse('delivery:store_chat_thread', args=[thread.id])
    except Exception:
        url = ''
    notify(recipient, title, url, 'chat')
