import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


CATEGORY_CHOICES = [
    ('bogcha_davlat', _("🏛️ Davlat bog'chasi")),
    ('bogcha_shaxsiy', _("🧸 Shaxsiy bog'cha")),
    ('kurs', _("📚 O'quv kurslari")),
    ('maktab', _("🏫 Maktab / litsey")),
]

# Bazadagi eski yozuvlarda uchraydigan kategoriyalar — chip'larda ko'rsatilmaydi,
# lekin get_category_display to'g'ri nom qaytarishi uchun choices'ga kiradi.
LEGACY_CATEGORY_CHOICES = [
    ('bogcha', _("🧒 Bog'cha")),
    ('boshqa', _("📦 Boshqa")),
    ('internet', _("🌐 Internet")),
    ('kommunal', _("💡 Kommunal")),
]

ALL_CATEGORY_CHOICES = CATEGORY_CHOICES + LEGACY_CATEGORY_CHOICES

# Online to'lov (ism-familiya + karta) qabul qiladigan kategoriyalar.
# Davlat bog'chasi bu ro'yxatda yo'q — u faqat ma'lumot uchun ko'rsatiladi.
PAYABLE_CATEGORIES = {'bogcha_shaxsiy', 'kurs', 'maktab'}


class Provider(models.Model):
    """To'lov qabul qiluvchi muassasa/xizmat (admin tomonidan kiritiladi).

    Kommunal, kurs, bog'cha, maktab, internet va boshqa to'lovlar shu yerda.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='Nomi')
    category = models.CharField(max_length=20, choices=ALL_CATEGORY_CHOICES, db_index=True, verbose_name='Turi')
    description = models.TextField(blank=True, verbose_name='Tavsif')
    address = models.CharField(max_length=300, blank=True, verbose_name='Manzil')
    phone = models.CharField(max_length=30, blank=True, verbose_name='Telefon')
    logo = models.ImageField(upload_to='payments/logos/', blank=True, null=True)
    amount = models.BigIntegerField(
        default=0, verbose_name="Belgilangan summa (so'm)",
        help_text="0 bo'lsa — foydalanuvchi summani o'zi kiritadi (oylik/erkin to'lov)",
    )
    region = models.CharField(max_length=100, blank=True, default='Shofirkon', verbose_name='Hudud')
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments_providers'
        verbose_name = 'Muassasa / xizmat'
        verbose_name_plural = 'Muassasalar / xizmatlar'
        ordering = ['category', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_category_display()})'

    @property
    def has_fixed_amount(self):
        return self.amount and self.amount > 0

    @property
    def is_payable(self):
        """Online to'lov qabul qiladimi? Davlat bog'chasi — yo'q (faqat ma'lumot)."""
        return self.category in PAYABLE_CATEGORIES


class ServicePayment(models.Model):
    """To'lov yozuvi (demo). DIQQAT: to'liq karta raqami va CVV SAQLANMAYDI —
    faqat oxirgi 4 raqam saqlanadi. Payme/Click keyinroq ulanadi."""
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('paid', "To'langan"),
        ('failed', 'Xato'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='service_payments',
    )
    provider = models.ForeignKey(
        Provider, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments',
    )
    provider_name = models.CharField(max_length=200, verbose_name='Muassasa nomi')
    category = models.CharField(max_length=20, choices=ALL_CATEGORY_CHOICES, db_index=True)
    first_name = models.CharField(max_length=80, blank=True, verbose_name='Ism')
    last_name = models.CharField(max_length=80, blank=True, verbose_name='Familiya')
    payer_name = models.CharField(
        max_length=150, blank=True, verbose_name="To'lovchi (ism-familiya)",
        help_text="Bola / o'quvchi ism-familiyasi (ism va familiyadan avtomatik tuziladi)",
    )
    period = models.CharField(max_length=20, blank=True, verbose_name='Davr (YYYY-MM)')
    amount = models.BigIntegerField(verbose_name="Summa (so'm)")
    card_holder = models.CharField(max_length=120, blank=True, verbose_name='Karta egasi')
    card_last4 = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payments_records'
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.provider_name} — {self.amount} so\'m'

    @staticmethod
    def detect_brand(card_number):
        digits = ''.join(c for c in (card_number or '') if c.isdigit())
        if digits.startswith('8600'):
            return 'Uzcard'
        if digits.startswith('9860'):
            return 'Humo'
        if digits.startswith('4'):
            return 'Visa'
        if digits.startswith('5'):
            return 'Mastercard'
        return 'Karta'


class Transaction(models.Model):
    """Payme / Click to'lov tranzaksiyasi (universal).

    Bir nechta tur uchun ishlaydi (delivery buyurtma, taksi, bron, xizmat
    to'lovi) — `target_type` + `target_id` orqali bog'lanadi (payments.gateways).

    state (Payme semantikasi): 1 = yaratilgan, 2 = bajarilgan (to'langan),
    -1 = yaratilgandan keyin bekor qilingan, -2 = bajarilgandan keyin bekor.
    """
    PROVIDER_CHOICES = [('payme', 'Payme'), ('click', 'Click')]

    STATE_CREATED = 1
    STATE_PERFORMED = 2
    STATE_CANCELED = -1
    STATE_CANCELED_AFTER_PERFORM = -2

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES, db_index=True)
    # Provayder bergan tranzaksiya identifikatori (Payme _id / Click click_trans_id)
    provider_transaction_id = models.CharField(max_length=64, db_index=True)
    target_type = models.CharField(max_length=20)   # order / trip / booking / service
    target_id = models.CharField(max_length=64, db_index=True)
    amount = models.BigIntegerField(verbose_name="Summa (so'm)")
    state = models.IntegerField(default=STATE_CREATED, db_index=True)
    reason = models.IntegerField(null=True, blank=True)  # Payme cancel sababi
    # Payme vaqtlari (ms). Click uchun ham create vaqti shu yerda saqlanadi.
    payme_time = models.BigIntegerField(null=True, blank=True)
    performed_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments_transactions'
        verbose_name = 'To\'lov tranzaksiyasi'
        verbose_name_plural = 'To\'lov tranzaksiyalari'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'provider_transaction_id'],
                name='uniq_provider_tx',
            ),
        ]

    def __str__(self):
        return f'{self.provider}:{self.provider_transaction_id} ({self.state})'
