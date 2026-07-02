from django.db import models


class TelegramLink(models.Model):
    """Telefon raqami ↔ Telegram chat bog'lanishi.

    Foydalanuvchi botga "📱 Raqamni ulashish" tugmasi orqali raqamini ulaganda
    yoziladi. Kod yuborishda shu jadval orqali chat_id topilib, OTP Telegram
    orqali yuboriladi (aks holda SMS'ga qaytiladi).

    `phone` — '998XXXXXXXXX' normal ko'rinishida saqlanadi (sms.normalize_phone).
    """
    phone = models.CharField(max_length=20, unique=True, db_index=True, verbose_name='Telefon')
    chat_id = models.BigIntegerField(verbose_name='Telegram chat ID')
    telegram_username = models.CharField(max_length=64, blank=True, verbose_name='Username')
    linked_at = models.DateTimeField(auto_now=True, verbose_name='Ulangan vaqti')

    class Meta:
        db_table = 'telegram_links'
        verbose_name = 'Telegram bog\'lanish'
        verbose_name_plural = 'Telegram bog\'lanishlar'
        ordering = ['-linked_at']

    def __str__(self):
        uname = f' (@{self.telegram_username})' if self.telegram_username else ''
        return f'{self.phone} → chat {self.chat_id}{uname}'
