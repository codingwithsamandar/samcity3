from django.db import models
from django.conf import settings


class Notification(models.Model):
    CATEGORY_CHOICES = [
        ('order', 'Buyurtma'),
        ('booking', 'Bron'),
        ('taxi', 'Taksi'),
        ('chat', 'Chat'),
        ('business', 'Biznes'),
        ('system', 'Tizim'),
    ]
    ICONS = {
        'order': '🧾', 'booking': '📅', 'taxi': '🚕',
        'chat': '💬', 'business': '🏪', 'system': '🔔',
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


def notify(recipient, text, url='', category='system'):
    """Bildirishnoma yaratish uchun yordamchi. recipient None bo'lsa — o'tkazib yuboradi.

    Bildirishnoma bazaga yoziladi va (kanal qatlami mavjud bo'lsa) real vaqtda
    foydalanuvchining WebSocket guruhiga yuboriladi.
    """
    if recipient is None:
        return None
    notification = Notification.objects.create(
        recipient=recipient, text=text, url=url or '', category=category,
    )
    _push_realtime(notification)
    return notification
