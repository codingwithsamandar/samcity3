import uuid
from django.db import models
from django.conf import settings
from django.db.models import Avg
from django.core.validators import MinValueValidator, MaxValueValidator


# ─────────────────────────────────────────────────────────────────────────────
#  TAKSI XIZMATLARI (dispatch / qisqa raqamli — 1265, 1187 kabilar)
# ─────────────────────────────────────────────────────────────────────────────
class TaxiService(models.Model):
    """Taksi xizmati / dispetcher kompaniya (masalan 1265, 1187).

    To'liq ma'lumot: boshlang'ich narx, har km narxi, ish vaqti, telefon,
    o'rtacha baho va sharhlar (review modeli orqali).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, verbose_name='Nomi')
    short_number = models.CharField(
        max_length=10, blank=True, db_index=True,
        verbose_name='Qisqa raqam',
        help_text='Masalan: 1265, 1187',
    )
    phone = models.CharField(max_length=30, blank=True, verbose_name='Telefon')
    logo = models.ImageField(upload_to='taxi/services/', blank=True, null=True)
    description = models.TextField(blank=True, verbose_name='Tavsif')
    base_price = models.BigIntegerField(
        default=0, verbose_name="Boshlang'ich narx (so'm)",
        help_text="Mashinaga o'tirish/chaqirish narxi",
    )
    price_per_km = models.BigIntegerField(
        default=0, verbose_name="Har km uchun narx (so'm)",
    )
    working_hours = models.CharField(
        max_length=100, blank=True, default='24/7', verbose_name='Ish vaqti',
    )
    region = models.CharField(
        max_length=100, blank=True, default='Shofirkon', verbose_name='Hudud',
    )
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'taxi_services'
        verbose_name = 'Taksi xizmati'
        verbose_name_plural = 'Taksi xizmatlari'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.short_number})' if self.short_number else self.name

    @property
    def avg_rating(self):
        r = self.reviews.aggregate(a=Avg('rating'))['a']
        return round(r, 1) if r else 0

    @property
    def review_count(self):
        return self.reviews.count()

    def example_price(self, km=5):
        """Namuna: km uchun taxminiy narx."""
        return self.base_price + self.price_per_km * km

    @property
    def example_5km(self):
        return self.base_price + self.price_per_km * 5


class ServiceReview(models.Model):
    """Taksi xizmatiga (1265 kabi) qoldirilgan baho va sharh."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(
        TaxiService, on_delete=models.CASCADE, related_name='reviews',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='taxi_service_reviews',
    )
    rating = models.PositiveSmallIntegerField(
        default=5, verbose_name='Baho (1-5)',
        choices=[(i, str(i)) for i in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True, verbose_name='Izoh')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'taxi_service_reviews'
        verbose_name = 'Xizmat sharhi'
        verbose_name_plural = 'Xizmat sharhlari'
        ordering = ['-created_at']
        unique_together = [('service', 'user')]

    def __str__(self):
        return f'{self.service} — {self.rating}★'


# ─────────────────────────────────────────────────────────────────────────────
#  TAKSISTLAR (AB punktlarda turadigan haydovchilar)
# ─────────────────────────────────────────────────────────────────────────────
class Taxist(models.Model):
    """A punktda turib B punktga olib boradigan taksist.

    To'liq ma'lumot: nechta odam tashigan (trips_count), o'rtacha baho,
    sharhlar, hamda AB marshrutlari (Route modeli orqali).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='taxist_profiles',
        verbose_name='Foydalanuvchi (ixtiyoriy)',
    )
    service = models.ForeignKey(
        TaxiService, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='taxists', verbose_name='Bog\'liq xizmat (ixtiyoriy)',
    )
    full_name = models.CharField(max_length=120, verbose_name='Ism familiya')
    phone = models.CharField(max_length=30, verbose_name='Telefon')
    car_model = models.CharField(max_length=120, blank=True, verbose_name='Mashina turi/modeli')
    photo = models.ImageField(upload_to='taxi/taxists/', blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, default='Shofirkon', verbose_name='Hudud')
    trips_count = models.PositiveIntegerField(
        default=0, verbose_name='Tashilgan yo\'lovchilar soni',
    )
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    # ── Live location (ride-hailing) ─────────────────────────────────────────
    is_online = models.BooleanField(default=False, db_index=True, verbose_name='Onlayn (buyurtma qabul qiladi)')
    latitude = models.FloatField(null=True, blank=True,
                                 validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(null=True, blank=True,
                                  validators=[MinValueValidator(-180), MaxValueValidator(180)])
    location_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'taxi_taxists'
        verbose_name = 'Taksist'
        verbose_name_plural = 'Taksistlar'
        ordering = ['-trips_count', 'full_name']

    def __str__(self):
        return self.full_name

    @property
    def avg_rating(self):
        r = self.reviews.aggregate(a=Avg('rating'))['a']
        return round(r, 1) if r else 0

    @property
    def review_count(self):
        return self.reviews.count()


class Route(models.Model):
    """AB punkt: taksist A punktdan B punktga narx va dostavka narxini belgilaydi."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    taxist = models.ForeignKey(
        Taxist, on_delete=models.CASCADE, related_name='routes',
    )
    point_a = models.CharField(max_length=150, verbose_name='A punkt (qayerdan)')
    point_b = models.CharField(max_length=150, verbose_name='B punkt (qayerga)')
    passenger_price = models.BigIntegerField(
        verbose_name="Yo'lovchi narxi (so'm)",
        help_text='Bir kishini A dan B ga olib borish narxi',
    )
    delivery_price = models.BigIntegerField(
        null=True, blank=True, verbose_name="Dostavka narxi (so'm)",
        help_text='Pochta/yuk yetkazish narxi',
    )
    note = models.CharField(max_length=200, blank=True, verbose_name='Izoh')
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'taxi_routes'
        verbose_name = 'AB marshrut'
        verbose_name_plural = 'AB marshrutlar'
        ordering = ['point_a', 'point_b']

    def __str__(self):
        return f'{self.point_a} → {self.point_b}'


class TaxistReview(models.Model):
    """Taksistga qoldirilgan baho va sharh."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    taxist = models.ForeignKey(
        Taxist, on_delete=models.CASCADE, related_name='reviews',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='taxist_reviews',
    )
    rating = models.PositiveSmallIntegerField(
        default=5, verbose_name='Baho (1-5)',
        choices=[(i, str(i)) for i in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True, verbose_name='Izoh')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'taxi_taxist_reviews'
        verbose_name = 'Taksist sharhi'
        verbose_name_plural = 'Taksist sharhlari'
        ordering = ['-created_at']
        unique_together = [('taxist', 'user')]

    def __str__(self):
        return f'{self.taxist} — {self.rating}★'

    @staticmethod
    def can_review(user, taxist):
        """Faqat shu taksist bilan sayohatni YAKUNLAGAN foydalanuvchi baho bera oladi."""
        if not user.is_authenticated:
            return False
        return Trip.objects.filter(
            passenger=user, taxist=taxist, status='completed',
        ).exists()


# ─────────────────────────────────────────────────────────────────────────────
#  MASHINA (taksist avtomobili — Yandex uslubida batafsil)
# ─────────────────────────────────────────────────────────────────────────────
class Car(models.Model):
    CLASS_CHOICES = [
        ('econom', 'Ekonom'),
        ('comfort', 'Komfort'),
        ('comfort_plus', 'Komfort+'),
        ('business', 'Biznes'),
        ('minivan', 'Miniven'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    taxist = models.OneToOneField(
        Taxist, on_delete=models.CASCADE, related_name='car',
    )
    brand = models.CharField(max_length=60, verbose_name='Marka', help_text='Masalan: Chevrolet')
    model = models.CharField(max_length=60, verbose_name='Model', help_text='Masalan: Cobalt')
    color = models.CharField(max_length=40, blank=True, verbose_name='Rangi')
    plate_number = models.CharField(max_length=20, blank=True, verbose_name='Davlat raqami')
    year = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='Ishlab chiqarilgan yili',
        validators=[MinValueValidator(1980), MaxValueValidator(2030)],
    )
    seats = models.PositiveSmallIntegerField(default=4, verbose_name="O'rindiqlar soni")
    car_class = models.CharField(max_length=20, choices=CLASS_CHOICES, default='econom', verbose_name='Tarif')
    has_conditioner = models.BooleanField(default=False, verbose_name='Konditsioner')
    has_baby_seat = models.BooleanField(default=False, verbose_name='Bolalar o\'rindig\'i')
    allows_pets = models.BooleanField(default=False, verbose_name='Hayvonlar bilan')
    photo = models.ImageField(upload_to='taxi/cars/', blank=True, null=True)

    class Meta:
        db_table = 'taxi_cars'
        verbose_name = 'Mashina'
        verbose_name_plural = 'Mashinalar'

    def __str__(self):
        return f'{self.brand} {self.model} ({self.plate_number})'

    @property
    def full_name(self):
        return f'{self.brand} {self.model}'.strip()


# ─────────────────────────────────────────────────────────────────────────────
#  SAYOHAT / BUYURTMA (Yandex order)
# ─────────────────────────────────────────────────────────────────────────────
class Trip(models.Model):
    STATUS_CHOICES = [
        ('searching', 'Qidirilmoqda'),
        ('accepted', 'Qabul qilindi'),
        ('on_way', "Yo'lda"),
        ('completed', 'Yakunlandi'),
        ('cancelled', 'Bekor qilindi'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Naqd pul'),
        ('card', 'Bank kartasi'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', "To'lanmagan"),
        ('paid', "To'langan"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    passenger = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='taxi_trips',
    )
    taxist = models.ForeignKey(Taxist, on_delete=models.CASCADE, related_name='trips')
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True, related_name='trips')
    point_a = models.CharField(max_length=150, verbose_name='A punkt')
    point_b = models.CharField(max_length=150, verbose_name='B punkt')
    pickup_lat = models.FloatField(null=True, blank=True,
                                   validators=[MinValueValidator(-90), MaxValueValidator(90)])
    pickup_lng = models.FloatField(null=True, blank=True,
                                   validators=[MinValueValidator(-180), MaxValueValidator(180)])
    dest_lat = models.FloatField(null=True, blank=True,
                                 validators=[MinValueValidator(-90), MaxValueValidator(90)])
    dest_lng = models.FloatField(null=True, blank=True,
                                 validators=[MinValueValidator(-180), MaxValueValidator(180)])
    distance_km = models.FloatField(null=True, blank=True)
    is_delivery = models.BooleanField(default=False, verbose_name='Dostavka buyurtmasi')
    price = models.BigIntegerField(verbose_name="Narx (so'm)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='accepted', db_index=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='card')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='unpaid', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'taxi_trips'
        verbose_name = 'Sayohat'
        verbose_name_plural = 'Sayohatlar'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['passenger', '-created_at'], name='trip_passenger_created_idx'),
            models.Index(fields=['taxist', 'status'], name='trip_taxist_status_idx'),
        ]

    def __str__(self):
        return f'{self.point_a} → {self.point_b} ({self.get_status_display()})'

    @property
    def is_paid(self):
        return self.payment_status == 'paid'

    @property
    def can_be_reviewed(self):
        return self.status == 'completed'


# ─────────────────────────────────────────────────────────────────────────────
#  TO'LOV (karta — simulyatsiya, Payme/Click keyinroq ulanadi)
# ─────────────────────────────────────────────────────────────────────────────
class Payment(models.Model):
    """To'lov yozuvi. DIQQAT: to'liq karta raqami va CVV SAQLANMAYDI —
    faqat oxirgi 4 raqam va karta egasi saqlanadi (xavfsizlik uchun)."""
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('paid', "To'langan"),
        ('failed', 'Xato'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='payment')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='taxi_payments')
    amount = models.BigIntegerField(verbose_name="Summa (so'm)")
    card_holder = models.CharField(max_length=120, blank=True, verbose_name='Karta egasi')
    card_last4 = models.CharField(max_length=4, blank=True, verbose_name='Karta oxirgi 4 raqami')
    card_brand = models.CharField(max_length=20, blank=True, verbose_name='Karta turi')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'taxi_payments'
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.amount} so\'m — {self.get_status_display()}'

    @staticmethod
    def detect_brand(card_number):
        """Karta raqamining birinchi raqamlari bo'yicha turini aniqlaydi."""
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
