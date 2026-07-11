from django.db import models
from django.conf import settings


class Notification(models.Model):
    CATEGORY_CHOICES = [
        ('order', 'Buyurtma'),
        ('booking', 'Bron'),
        ('taxi', 'Taksi'),
        ('chat', 'Chat'),
        ('business', 'Biznes'),
        ('ads', 'Reklama'),
        ('system', 'Tizim'),
    ]
    ICONS = {
        'order': '🧾', 'booking': '📅', 'taxi': '🚕',
        'chat': '💬', 'business': '🏪', 'ads': '📣', 'system': '🔔',
    }

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications',
    )
    text = models.CharField(max_length=255)
    url = models.CharField(max_length=300, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='system')
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        verbose_name = 'Bildirishnoma'
        verbose_name_plural = 'Bildirishnomalar'

    def __str__(self):
        return f'{self.recipient} — {self.text[:40]}'

    @property
    def icon(self):
        return self.ICONS.get(self.category, '🔔')


def _push_realtime(notification):
    """Push a notification to the recipient's WebSocket group (best-effort)."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        if layer is None:
            return
        unread = notification.recipient.notifications.filter(is_read=False).count()
        async_to_sync(layer.group_send)(
            f'notif_user_{notification.recipient_id}',
            {
                'type': 'notify_message',
                'text': notification.text,
                'url': notification.url,
                'category': notification.category,
                'icon': notification.icon,
                'count': unread,
            },
        )
    except Exception:
        # WebSocket delivery is best-effort; the DB row is the source of truth.
        pass


class DeviceToken(models.Model):
    """Mobil qurilmaning FCM push tokeni.

    Mobil ilova login'dan keyin POST /api/notifications/device/ ga tokenini
    yuboradi; logout'da DELETE bilan o'chiradi. Yuborish: notifications/push.py
    (FIREBASE_CREDENTIALS_FILE sozlanmaguncha jimgina o'chiq).
    """
    PLATFORM_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='device_tokens',
    )
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default='android')
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_device_tokens'
        ordering = ['-last_seen_at']
        verbose_name = 'Qurilma tokeni (push)'
        verbose_name_plural = 'Qurilma tokenlari (push)'

    def __str__(self):
        return f'{self.user} — {self.platform} — {self.token[:16]}…'


def _push_fcm(notification):
    """FCM push (best-effort). Firebase sozlanmagan bo'lsa hech narsa qilmaydi."""
    try:
        from .push import send_push
        send_push(
            notification.recipient,
            title='SamCity',
            body=notification.text,
            data={
                'url': notification.url,
                'category': notification.category,
                'notification_id': str(notification.pk),
            },
        )
    except Exception:
        # Push best-effort; bazadagi yozuv — asosiy manba.
        pass


def notify(recipient, text, url='', category='system'):
    """Bildirishnoma yaratish uchun yordamchi. recipient None bo'lsa — o'tkazib yuboradi.

    Bildirishnoma bazaga yoziladi va (kanal qatlami mavjud bo'lsa) real vaqtda
    foydalanuvchining WebSocket guruhiga, hamda (Firebase sozlangan bo'lsa)
    qurilmalarga FCM push sifatida yuboriladi.
    """
    if recipient is None:
        return None
    notification = Notification.objects.create(
        recipient=recipient, text=text, url=url or '', category=category,
    )
    _push_realtime(notification)
    _push_fcm(notification)
    return notification
