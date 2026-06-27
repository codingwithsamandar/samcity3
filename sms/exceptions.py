class SMSError(Exception):
    """SMS yuborishda umumiy xatolik."""


class SMSAuthError(SMSError):
    """Provayder autentifikatsiyasi muvaffaqiyatsiz (login/token)."""


class SMSConfigError(SMSError):
    """Sozlama yetishmaydi (login/parol/.env to'ldirilmagan)."""
