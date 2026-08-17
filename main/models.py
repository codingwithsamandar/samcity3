import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from .utils import validate_file_type

# Telefon raqami validatori (ixtiyoriy +, 9-15 raqam). Forma/full_clean da ishlaydi.
phone_validator = RegexValidator(
    r'^\+?\d{9,15}$',
    "Telefon raqamini to'g'ri kiriting (masalan: +998901234567).",
)


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra):
        if not phone:
            raise ValueError('Phone required')
        user = self.model(phone=phone, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('role', 'admin')
        return self.create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('user', 'Foydalanuvchi'),
        ('business', 'Biznes'),
        ('driver', 'Haydovchi'),
        ('admin', 'Admin'),
    ]
    GENDER_CHOICES = [
        ('male', 'Erkak'),
        ('female', 'Ayol'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=15, unique=True, validators=[phone_validator])
    name = models.CharField(max_length=100, blank=True)
    username = models.CharField(max_length=50, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', blank=True, null=True, validators=[validate_file_type])
    avatar_url = models.TextField(blank=True)
    # Reklama auditoriyasini ajratish uchun (ixtiyoriy — profilda to'ldiriladi).
    gender = models.CharField('Jins', max_length=10, choices=GENDER_CHOICES, blank=True)
    birth_date = models.DateField("Tug'ilgan sana", null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    # Foydalanuvchi tanlagan "o'z mahallasi" — chatda tepada pin/ajratib ko'rsatiladi.
    neighborhood = models.ForeignKey(
        'Neighborhood', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='residents', verbose_name='Mahalla',
    )
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0,
                                 validators=[MinValueValidator(0), MaxValueValidator(5)])
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    groups = models.ManyToManyField(
        'auth.Group', blank=True,
        related_name='main_user_set', related_query_name='main_user',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission', blank=True,
        related_name='main_user_permissions', related_query_name='main_user_perm',
        verbose_name='user permissions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        db_table = 'users'
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def __str__(self):
        return self.name or self.phone

    def get_full_name(self):
        return self.name or ''

    @property
    def age(self):
        """Tug'ilgan sanadan yoshni hisoblaydi (yo'q bo'lsa None)."""
        if not self.birth_date:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day))

    def save(self, *args, **kwargs):
        # role='admin' bo'lsa is_staff ham yoqilsin — aks holda admin/Analitika
        # paneli ko'rinmaydi (is_staff tekshiriladi). Faqat qo'shadi, olib tashlamaydi.
        if self.role == 'admin' and not self.is_staff:
            self.is_staff = True
        super().save(*args, **kwargs)


class OTPCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=15, db_index=True)
    code = models.CharField(max_length=6, validators=[RegexValidator(r'^\d{6}$', "OTP kod 6 ta raqamdan iborat bo'lishi kerak.")])
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'otp_codes'
        ordering = ['-created_at']


class Ad(models.Model):
    CATEGORY_CHOICES = [
        ('uy_joy', 'Uy-joy'), ('ish', 'Ish'), ('avtomobil', 'Avtomobil'),
        ('qishloq', "Qishloq xo'jaligi"),
        ('xizmat', 'Xizmat'), ('hayvonlar', 'Hayvonlar'), ('boshqa', 'Boshqa'),
    ]
    PRICE_TYPE_CHOICES = [('fixed', 'Belgilangan'), ('free', 'Bepul')]
    STATUS_CHOICES = [('active', 'Faol'), ('sold', 'Sotilgan'), ('expired', "Muddati o'tgan"), ('deleted', "O'chirilgan")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ads')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.BigIntegerField(blank=True, null=True)
    price_type = models.CharField(max_length=20, choices=PRICE_TYPE_CHOICES, default='fixed')
    location = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField(blank=True, null=True,
                                 validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(blank=True, null=True,
                                  validators=[MinValueValidator(-180), MaxValueValidator(180)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    views = models.PositiveIntegerField(default=0)
    is_boosted = models.BooleanField(default=False)
    boosted_until = models.DateTimeField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_telegram = models.CharField(max_length=100, blank=True)
    contact_instagram = models.CharField(max_length=100, blank=True)
    sold_at = models.DateTimeField(blank=True, null=True)
    contact_count = models.PositiveIntegerField(default=0, verbose_name='Kontakt ko\'rishlar')
    # Task 23 FIX: venue_booking_enabled field (migration 0007 da bor, models.py dan tushib qolgan)
    venue_booking_enabled = models.BooleanField(default=True, verbose_name='Venue bron tizimi')
    venue_price_per_day = models.BigIntegerField(null=True, blank=True, verbose_name="Narx (kunlik, so'm)")
    venue_price_per_hour = models.BigIntegerField(null=True, blank=True, verbose_name="Narx (soatlik, so'm)")
    venue_capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name="Sig'imlilik (kishi)")
    cancellation_policy = models.CharField(
        max_length=20,
        choices=[
            ('flexible', "Moslashuvchan (1 kun oldin — 100% qaytarish)"),
            ('moderate', "O'rtacha (3 kun oldin — 50% qaytarish)"),
            ('strict',   "Qattiq (7 kun oldin — 25% qaytarish)"),
        ],
        default='moderate',
        verbose_name='Bekor qilish siyosati',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ads'
        ordering = ['-is_boosted', '-created_at']
        indexes = [
            # Marketplace ro'yxati: status bo'yicha filtr + boost/created bo'yicha tartib
            models.Index(fields=['status', '-is_boosted', '-created_at'], name='ad_status_boost_created_idx'),
            models.Index(fields=['user', 'status'], name='ad_user_status_idx'),
        ]

    def __str__(self):
        return self.title


class AdImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='ads/%Y/%m/', validators=[validate_file_type])
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_images'
        ordering = ['order']


class District(models.Model):
    """Tuman (masalan «Shofirkon tumani») — mahallalarni birlashtiradi.

    Tuman hokimi shu tuman doirasidagi BARCHA mahalla aholisiga (o'z mahallasi
    sifatida shu tumandagi biror mahallani tanlagan foydalanuvchilarga) rasmiy
    e'lon/bildirishnoma yubora oladi."""
    name = models.CharField('Tuman nomi', max_length=120)
    description = models.TextField('Tavsif', blank=True)
    head_name = models.CharField('Hokim (F.I.O.)', max_length=120, blank=True)
    head_phone = models.CharField('Hokim telefoni', max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'districts'
        verbose_name = 'Tuman'
        verbose_name_plural = 'Tumanlar'
        ordering = ['name']

    def __str__(self):
        return self.name

    def is_admin(self, user):
        """Foydalanuvchi shu tuman hokimimi (e'lon boshqaruvi uchun).

        Staff yoki shu tumanning DistrictAdmin'i (hokimi) admin hisoblanadi."""
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        return self.admins.filter(user=user).exists()

    def residents(self):
        """Shu tumandagi biror mahallani «o'z mahallam» qilib tanlagan aholi (QS)."""
        return User.objects.filter(
            neighborhood__district=self, is_active=True,
        ).distinct()


class Neighborhood(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='neighborhoods', verbose_name='Tuman',
    )
    # ── Xaritadagi joylashuv va chegara ──────────────────────────────────────
    center_lat = models.FloatField('Markaz (kenglik)', null=True, blank=True)
    center_lng = models.FloatField('Markaz (uzunlik)', null=True, blank=True)
    # Chegara — poligon nuqtalari ro'yxati: [[lat, lng], [lat, lng], ...]
    boundary = models.JSONField('Chegara (poligon)', null=True, blank=True, default=None)
    color = models.CharField('Rang', max_length=9, blank=True, default='#3551d1')
    # ── Mahalla ma'lumotlari (Mahalla sahifasi uchun) ────────────────────────
    population = models.PositiveIntegerField('Aholi soni', null=True, blank=True)
    head_name = models.CharField('Mahalla raisi', max_length=120, blank=True)
    head_phone = models.CharField('Rais telefoni', max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'neighborhoods'
        verbose_name = 'Mahalla'
        verbose_name_plural = 'Mahallalar'
        # Tartibsiz qolsa Postgres qatorlarni har UPDATE'dan keyin boshqacha
        # qaytarishi mumkin — mahalla grid'i va barcha dropdown'lar joyini
        # o'zgartirib turardi.
        ordering = ['name']

    def __str__(self):
        return self.name

    def boundary_latlng(self):
        """Leaflet uchun [[lat,lng],...] qaytaradi (yoki bo'sh ro'yxat)."""
        return self.boundary or []

    def centroid(self):
        """Markaz nuqtasi — chegara bo'lsa undan, aks holda center maydonidan."""
        pts = self.boundary or []
        if pts:
            return [round(sum(p[0] for p in pts) / len(pts), 6),
                    round(sum(p[1] for p in pts) / len(pts), 6)]
        if self.center_lat is not None and self.center_lng is not None:
            return [self.center_lat, self.center_lng]
        return None

    def bbox(self):
        """Chegarani qamrab oluvchi to'rtburchak: (lat_min, lat_max, lng_min, lng_max).

        `contains_point` ray-casting'i Python'da ishlaydi — uni butun jadvalga
        yugurtirmaslik uchun avval SQL darajasida shu to'rtburchak bilan
        filtrlanadi. Chegara yo'q bo'lsa None."""
        ring = self.boundary or []
        if not ring:
            return None
        lats = [p[0] for p in ring]
        lngs = [p[1] for p in ring]
        return (min(lats), max(lats), min(lngs), max(lngs))

    def contains_point(self, lat, lng):
        """Nuqta (lat,lng) mahalla chegarasi ichidami? (ray-casting).

        Do'kon/joylarni FK'siz, faqat koordinata bo'yicha mahallaga bog'lash uchun
        (places.neighborhood_places_geojson bilan bir xil algoritm)."""
        ring = self.boundary or []
        if not ring or lat is None or lng is None:
            return False
        inside = False
        j = len(ring) - 1
        for i in range(len(ring)):
            yi, xi = ring[i][0], ring[i][1]
            yj, xj = ring[j][0], ring[j][1]
            if (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
        return inside

    def is_admin(self, user):
        """Foydalanuvchi shu mahalla admini (raisi)mi — e'lon/murojaat boshqaruvi uchun.

        Staff yoki shu mahallaning ChatAdmin'i (mavjud infra) admin hisoblanadi."""
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        return self.admins.filter(user=user).exists()

    # Eslatma: shu mahallani «o'z mahallam» qilib tanlagan aholi — `self.residents`
    # reverse manager orqali (User.neighborhood related_name='residents').
    # Rasmiy e'lon aynan shularga boradi (chat a'zoligiga bog'liq emas).


class ChatAdmin(models.Model):
    """Mahalla admini (raisi) — mahalla bo'yicha tayinlanadi.

    Neighborhood.is_admin() shu jadvalga tayanadi: rasmiy e'lon, fuqaro
    murojaatlari va mahalla do'kon arizalarini boshqarish huquqini beradi.
    (Model nomi/jadvali tarixiy — 'chat_admins' — backward-compat uchun saqlanadi.)
    """
    neighborhood = models.ForeignKey(Neighborhood, on_delete=models.CASCADE, related_name='admins')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_admin_roles')
    appointed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_admins'
        verbose_name = 'Chat admini'
        verbose_name_plural = 'Chat adminlari'
        unique_together = [('neighborhood', 'user')]

    def __str__(self):
        return f'{self.neighborhood.name} — Admin'


# ════════════════════════════════════════════════════════════════════════════
#  MAHALLA — rasmiy e'lonlar + fuqarolar murojaati (Mahalla sahifasi uchun)
# ════════════════════════════════════════════════════════════════════════════

class NeighborhoodAnnouncement(models.Model):
    """Mahalla raisi/admin tomonidan joylanadigan rasmiy e'lon.

    Masalan: suv o'chirilishi, umumiy yig'ilish sanasi, obodonlashtirish."""
    neighborhood = models.ForeignKey(
        Neighborhood, on_delete=models.CASCADE, related_name='announcements',
        verbose_name='Mahalla',
    )
    title = models.CharField(max_length=200, verbose_name='Sarlavha')
    text = models.TextField(verbose_name='Matn')
    image = models.ImageField(upload_to='mahalla/announcements/%Y/%m/', blank=True, null=True,
                              validators=[validate_file_type])
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='neighborhood_announcements',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'neighborhood_announcements'
        ordering = ['-created_at']
        verbose_name = "Mahalla e'loni"
        verbose_name_plural = "Mahalla e'lonlari"
        indexes = [models.Index(fields=['neighborhood', '-created_at'], name='nb_ann_created_idx')]

    def __str__(self):
        return f'{self.neighborhood.name}: {self.title}'


class DistrictAdmin(models.Model):
    """Tuman hokimi — tuman bo'yicha tayinlanadi (ChatAdmin bilan bir xil naqsh)."""
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='admins')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='district_admin_roles')
    appointed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'district_admins'
        verbose_name = 'Tuman hokimi'
        verbose_name_plural = 'Tuman hokimlari'
        unique_together = [('district', 'user')]

    def __str__(self):
        return f'{self.district.name} — Hokim ({self.user})'


class DistrictAnnouncement(models.Model):
    """Tuman hokimi tomonidan joylanadigan rasmiy e'lon (butun tuman aholisiga)."""
    district = models.ForeignKey(
        District, on_delete=models.CASCADE, related_name='announcements',
        verbose_name='Tuman',
    )
    title = models.CharField('Sarlavha', max_length=200)
    text = models.TextField('Matn')
    image = models.ImageField(upload_to='tuman/announcements/%Y/%m/', blank=True, null=True,
                              validators=[validate_file_type])
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='district_announcements',
    )
    # Bildirishnoma yuborilgan aholi soni (audit uchun).
    recipients_count = models.PositiveIntegerField('Yuborilganlar soni', default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'district_announcements'
        ordering = ['-created_at']
        verbose_name = "Tuman e'loni"
        verbose_name_plural = "Tuman e'lonlari"
        indexes = [models.Index(fields=['district', '-created_at'], name='dist_ann_created_idx')]

    def __str__(self):
        return f'{self.district.name}: {self.title}'


class CitizenRequest(models.Model):
    """Fuqaro murojaati/shikoyati — hokimiyat (mahalla) ishlariga yordam.

    Holat zanjiri: yuborildi → ko'rib chiqilmoqda → hal qilindi / rad etildi."""
    CATEGORY_CHOICES = [
        ('road', "Yo'l"),
        ('water', 'Suv'),
        ('electricity', 'Svet / elektr'),
        ('cleaning', 'Tozalik'),
        ('gas', 'Gaz'),
        ('lighting', "Ko'cha yoritilishi"),
        ('landscaping', 'Obodonlashtirish'),
        ('other', 'Boshqa'),
    ]
    STATUS_CHOICES = [
        ('submitted', 'Yuborildi'),
        ('reviewing', 'Ko\'rib chiqilmoqda'),
        ('resolved', 'Hal qilindi'),
        ('rejected', 'Rad etildi'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    neighborhood = models.ForeignKey(
        Neighborhood, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='citizen_requests', verbose_name='Mahalla',
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='citizen_requests')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', db_index=True)
    title = models.CharField(max_length=200, verbose_name='Mavzu')
    text = models.TextField(verbose_name='Murojaat matni')
    image = models.ImageField(upload_to='mahalla/requests/%Y/%m/', blank=True, null=True,
                              validators=[validate_file_type])
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='submitted', db_index=True)
    response = models.TextField(blank=True, verbose_name='Rais/admin javobi')
    responded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_requests',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'citizen_requests'
        ordering = ['-created_at']
        verbose_name = 'Fuqaro murojaati'
        verbose_name_plural = 'Fuqaro murojaatlari'
        indexes = [
            models.Index(fields=['neighborhood', 'status', '-created_at'], name='citizen_req_nb_status_idx'),
            models.Index(fields=['user', '-created_at'], name='citizen_req_user_idx'),
        ]

    def __str__(self):
        return f'{self.get_category_display()}: {self.title} [{self.get_status_display()}]'


# Murojaat holati o'tishlari (kim qaysi holatga o'tkaza oladi — admin).
CITIZEN_REQUEST_TRANSITIONS = {
    'submitted': {'reviewing', 'resolved', 'rejected'},
    'reviewing': {'resolved', 'rejected'},
    'resolved': set(),
    'rejected': set(),
}


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'), ('confirmed', 'Tasdiqlangan'),
        ('cancelled', 'Bekor qilindi'), ('completed', 'Yakunlandi'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='bookings')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_bookings')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_bookings')
    message = models.TextField(blank=True, verbose_name='Xabar')
    start_date = models.DateField(blank=True, null=True, verbose_name='Boshlanish sanasi')
    end_date = models.DateField(blank=True, null=True, verbose_name='Tugash sanasi')
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', "To'lanmagan"),
        ('held', "Platformada ushlab turilgan"),
        ('released', "Egaga o'tkazilgan"),
        ('refunded', "Qaytarilgan"),
        ('partial_refund', "Qisman qaytarilgan"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    guests = models.PositiveIntegerField(default=1, verbose_name='Mehmonlar soni')
    total_amount = models.BigIntegerField(null=True, blank=True, verbose_name="Umumiy summa (so'm)")
    platform_fee = models.BigIntegerField(default=0, verbose_name="Platforma komissiyasi (so'm)")
    owner_amount = models.BigIntegerField(default=0, verbose_name="Egaga o'tkaziladigan summa (so'm)")
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid', db_index=True,
        verbose_name="To'lov holati"
    )
    refund_amount = models.BigIntegerField(default=0, verbose_name="Qaytarilgan summa (so'm)")
    penalty_amount = models.BigIntegerField(default=0, verbose_name="Jarima summasi (so'm)")
    cancelled_by = models.CharField(
        max_length=10, choices=[('buyer', 'Mijoz'), ('owner', 'Egasi')],
        null=True, blank=True, verbose_name='Kim bekor qildi'
    )
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="To'lov vaqti")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings'
        verbose_name = 'Bron'
        verbose_name_plural = 'Bronlar'
        ordering = ['-created_at']


class JobAd(models.Model):
    JOB_TYPE_CHOICES = [
        ('full_time', "To'liq stavka"), ('part_time', 'Yarim stavka'),
        ('remote', 'Masofaviy'), ('contract', 'Shartnoma asosida'), ('temporary', 'Vaqtinchalik'),
    ]
    STATUS_CHOICES = [('active', 'Faol'), ('closed', 'Yopilgan'), ('deleted', "O'chirilgan")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_ads')
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    company_description = models.TextField(blank=True, verbose_name='Kompaniya haqida')
    manager_name = models.CharField(max_length=120, blank=True, verbose_name='Menejer ismi')
    manager_phone = models.CharField(max_length=30, blank=True, verbose_name='Menejer telefoni')
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default='full_time')
    salary_min = models.BigIntegerField(blank=True, null=True)
    salary_max = models.BigIntegerField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    deadline = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    views = models.PositiveIntegerField(default=0)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_telegram = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'job_ads'
        verbose_name = "Ish e'loni"
        verbose_name_plural = "Ish e'lonlari"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ResumeAd(models.Model):
    EXP_CHOICES = [
        ('no_exp', 'Tajribasiz'), ('1_year', '1 yilgacha'),
        ('1_3', '1–3 yil'), ('3_5', '3–5 yil'), ('5_plus', '5+ yil'),
    ]
    STATUS_CHOICES = [('active', 'Faol'), ('hired', 'Ishga joylashdi'), ('deleted', "O'chirilgan")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resume_ads')
    title = models.CharField(max_length=200)
    experience = models.CharField(max_length=20, choices=EXP_CHOICES, default='no_exp')
    salary_min = models.BigIntegerField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True)
    skills = models.TextField(blank=True)
    about = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    views = models.PositiveIntegerField(default=0)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_telegram = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'resume_ads'
        verbose_name = 'Resume'
        verbose_name_plural = 'Resumelar'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class UtilityPayment(models.Model):
    SERVICE_CHOICES = [
        ('elektr', '⚡ Elektr'), ('suv', '💧 Suv'), ('gaz', '🔥 Gaz'),
        ('internet', '🌐 Internet'), ('telefon', '📞 Telefon'),
        ('uy_fondi', '🏘️ Uy-joy fondi'), ('boshqa', '📋 Boshqa'),
    ]
    STATUS_CHOICES = [
        ('tolangan', "To'langan"), ('kutilmoqda', 'Kutilmoqda'),
        ('muddati_otgan', "Muddati o'tgan"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='utility_payments')
    service = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    amount = models.BigIntegerField(verbose_name="Summa (so'm)")
    period = models.CharField(max_length=7, verbose_name='Davr (YYYY-MM)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='tolangan')
    note = models.CharField(max_length=255, blank=True, verbose_name='Izoh')
    paid_at = models.DateField(verbose_name="To'lov sanasi")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'utility_payments'
        verbose_name = "Kommunal to'lov"
        verbose_name_plural = "Kommunal to'lovlar"
        ordering = ['-paid_at', '-created_at']


# ── Task 23: BoostPayment — monetizatsiya yozuvlari ─────────────────────────
class BoostPayment(models.Model):
    PLAN_CHOICES = [
        ('week',    '7 kunlik — 10,000 so\'m'),
        ('month',   '30 kunlik — 30,000 so\'m'),
        ('quarter', '90 kunlik — 75,000 so\'m'),
    ]
    STATUS_CHOICES = [
        ('pending',   'Kutilmoqda'),
        ('active',    'Faol'),
        ('expired',   'Muddati tugagan'),
        ('cancelled', 'Bekor qilindi'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='boost_payments')
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='boosts', null=True, blank=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    amount = models.BigIntegerField(verbose_name="To'lov summasi (so'm)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'boost_payments'
        verbose_name = 'Boost to\'lov'
        verbose_name_plural = 'Boost to\'lovlar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} — {self.plan} — {self.status}'


# ════════════════════════════════════════════════════════════════════════════
#  COMMUNITY — POLLS (so'rovnomalar)
# ════════════════════════════════════════════════════════════════════════════

class Poll(models.Model):
    TYPE_CHOICES = [('single', 'Bitta variant'), ('multiple', 'Bir nechta variant')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    neighborhood = models.ForeignKey(
        Neighborhood, on_delete=models.CASCADE, related_name='polls', null=True, blank=True,
    )
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='polls')
    question = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    poll_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='single')
    is_anonymous = models.BooleanField(default=False, verbose_name='Anonim ovoz berish')
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'community_polls'
        ordering = ['-created_at']
        verbose_name = "So'rovnoma"
        verbose_name_plural = "So'rovnomalar"

    def __str__(self):
        return self.question

    @property
    def is_expired(self):
        from django.utils import timezone as _tz
        return bool(self.expires_at and self.expires_at < _tz.now())

    @property
    def is_open(self):
        return self.is_active and not self.is_expired

    def total_votes(self):
        return PollVote.objects.filter(option__poll=self).values('user').distinct().count()


class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'community_poll_options'
        ordering = ['order', 'id']

    def __str__(self):
        return self.text

    def vote_count(self):
        return self.votes.count()


class PollVote(models.Model):
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='poll_votes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'community_poll_votes'
        unique_together = [('option', 'user')]


class PollComment(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='poll_comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'community_poll_comments'
        ordering = ['created_at']


# ════════════════════════════════════════════════════════════════════════════
#  COMMUNITY — HELP CENTER (yordam markazi)
# ════════════════════════════════════════════════════════════════════════════

class HelpRequest(models.Model):
    KIND_CHOICES = [('request', 'Yordam so\'rayman'), ('offer', 'Yordam taklif qilaman')]
    CATEGORY_CHOICES = [
        ('general', 'Umumiy yordam'),
        ('blood', 'Qon topshirish'),
        ('lost_found', 'Yo\'qolgan / topilgan'),
        ('emergency', 'Favqulodda'),
        ('elderly', 'Keksalarga yordam'),
        ('donation', 'Xayriya / ehson'),
        ('volunteer', 'Ko\'ngillilik'),
    ]
    STATUS_CHOICES = [
        ('open', 'Ochiq'),
        ('in_progress', 'Jarayonda'),
        ('resolved', 'Hal qilindi'),
        ('closed', 'Yopildi'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='help_requests')
    neighborhood = models.ForeignKey(
        Neighborhood, on_delete=models.SET_NULL, related_name='help_requests', null=True, blank=True,
    )
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default='request')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general', db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=300, blank=True)
    latitude = models.FloatField(null=True, blank=True,
                                 validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(null=True, blank=True,
                                  validators=[MinValueValidator(-180), MaxValueValidator(180)])
    phone = models.CharField(max_length=30, blank=True)
    image = models.ImageField(upload_to='help/%Y/%m/', blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open', db_index=True)
    is_urgent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'community_help_requests'
        ordering = ['-is_urgent', '-created_at']
        verbose_name = 'Yordam so\'rovi'
        verbose_name_plural = 'Yordam so\'rovlari'

    def __str__(self):
        return f'{self.get_category_display()}: {self.title}'

    def volunteer_count(self):
        return self.volunteers.count()


class HelpVolunteer(models.Model):
    request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, related_name='volunteers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='volunteering')
    message = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'community_help_volunteers'
        unique_together = [('request', 'user')]
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user} → {self.request}'


# ════════════════════════════════════════════════════════════════════════════
#  MARKETPLACE — Ad favorites / reports / inquiries  +  Search trends
# ════════════════════════════════════════════════════════════════════════════

class AdFavorite(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='favorited_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_ads')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_favorites'
        ordering = ['-created_at']
        unique_together = [('ad', 'user')]

    def __str__(self):
        return f'{self.user} ♥ {self.ad.title}'


class AdReport(models.Model):
    REASON_CHOICES = [
        ('spam', 'Spam / reklama'),
        ('scam', 'Firibgarlik'),
        ('duplicate', 'Takroriy e\'lon'),
        ('offensive', 'Nomaqbul kontent'),
        ('wrong_category', 'Noto\'g\'ri kategoriya'),
        ('other', 'Boshqa'),
    ]
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ad_reports')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='other')
    detail = models.CharField(max_length=500, blank=True)
    is_resolved = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_reports'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.ad.title} — {self.get_reason_display()}'


class AdInquiry(models.Model):
    """Buyer ↔ seller inquiry / negotiation thread for an ad."""
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='inquiries')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ad_inquiries')
    message = models.TextField()
    # Egasi (sotuvchi) markaziy "Kelgan savollar" bo'limida ko'rgan/ko'rmagani.
    # O'qilmaganlar soni badge sifatida ko'rsatiladi.
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_inquiries'
        ordering = ['created_at']
        indexes = [models.Index(fields=['ad', 'created_at'], name='ad_inq_ad_created_idx')]

    def __str__(self):
        return f'{self.sender} → {self.ad.title}'


class SearchQuery(models.Model):
    """Aggregated search terms for trending/suggestions."""
    term = models.CharField(max_length=120, unique=True, db_index=True)
    count = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'search_queries'
        ordering = ['-count']

    def __str__(self):
        return f'{self.term} ({self.count})'


# ════════════════════════════════════════════════════════════════════════════
#  REKLAMA KAMPANIYASI — auditoriyani ajratib, random N kishiga bildirishnoma
# ════════════════════════════════════════════════════════════════════════════

class AdCampaign(models.Model):
    """Reklama kampaniyasi (admin panelidan).

    Auditoriya jins/yosh/mahalla/tuman/rol bo'yicha ajratiladi; shu auditoriyadan
    tasodifiy `target_count` kishiga bildirishnoma (+ push) yuboriladi. Bir
    foydalanuvchi kuniga eng ko'pi bilan 1 ta reklama oladi (AdCampaignDelivery)."""
    GENDER_CHOICES = [('', 'Farqi yo\'q'), ('male', 'Erkak'), ('female', 'Ayol')]
    ROLE_CHOICES = [('', 'Farqi yo\'q'), ('user', 'Foydalanuvchi'),
                    ('business', 'Biznes'), ('driver', 'Haydovchi')]
    STATUS_CHOICES = [('draft', 'Qoralama'), ('sent', 'Yuborilgan')]

    title = models.CharField('Sarlavha', max_length=200)
    text = models.TextField('Matn')
    url = models.CharField('Havola (ixtiyoriy)', max_length=300, blank=True)
    image = models.ImageField('Rasm', upload_to='ads/campaigns/%Y/%m/', blank=True, null=True,
                              validators=[validate_file_type])

    # ── Auditoriya filtrlari ──
    gender = models.CharField('Jins', max_length=10, choices=GENDER_CHOICES, blank=True)
    age_min = models.PositiveIntegerField('Yosh (dan)', null=True, blank=True)
    age_max = models.PositiveIntegerField('Yosh (gacha)', null=True, blank=True)
    neighborhood = models.ForeignKey(
        Neighborhood, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ad_campaigns', verbose_name='Mahalla (ixtiyoriy)')
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ad_campaigns', verbose_name='Tuman (ixtiyoriy)')
    role = models.CharField('Rol', max_length=20, choices=ROLE_CHOICES, blank=True)

    # ── Yuborish parametrlari ──
    send_to_all = models.BooleanField(
        'Hammaga yuborish', default=False,
        help_text="Yoqilsa — filtrlarga mos BARCHA faol foydalanuvchiga bir vaqtda "
                  "yuboriladi (random N va kuniga-1 cheklovisiz). Filtrlar bo'sh "
                  "bo'lsa — butun bazadagi hamma foydalanuvchiga.")
    target_count = models.PositiveIntegerField('Nechta kishiga (random)', default=50)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', db_index=True)
    sent_count = models.PositiveIntegerField('Yuborildi (fakt)', default=0)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ad_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ad_campaigns'
        ordering = ['-created_at']
        verbose_name = 'Reklama kampaniyasi'
        verbose_name_plural = 'Reklama kampaniyalari'

    def __str__(self):
        return self.title

    def audience_queryset(self, exclude_recent=True):
        """Filtrlarga mos, faol foydalanuvchilar (yuborish uchun nomzodlar).

        `exclude_recent=True` bo'lsa — oxirgi 24 soatda ALLAQACHON biror reklama
        olgan foydalanuvchilar chiqarib tashlanadi (kuniga 1 ta cheklovi)."""
        from datetime import date, timedelta
        from django.utils import timezone
        qs = User.objects.filter(is_active=True)
        if self.gender:
            qs = qs.filter(gender=self.gender)
        if self.role:
            qs = qs.filter(role=self.role)
        if self.neighborhood_id:
            qs = qs.filter(neighborhood_id=self.neighborhood_id)
        if self.district_id:
            qs = qs.filter(neighborhood__district_id=self.district_id)
        # Yosh → tug'ilgan sana oralig'iga aylantiriladi (birth_date bor bo'lsa).
        today = date.today()

        def _birth_cutoff(age):
            # today - age yil. 29-fevralda (kabisa) xatolikni oldini olish uchun
            # 28-fevralga tushiramiz.
            try:
                return today.replace(year=today.year - age)
            except ValueError:
                return today.replace(year=today.year - age, day=28)

        if self.age_min is not None:
            qs = qs.filter(birth_date__isnull=False,
                           birth_date__lte=_birth_cutoff(self.age_min))
        if self.age_max is not None:
            qs = qs.filter(birth_date__isnull=False,
                           birth_date__gt=_birth_cutoff(self.age_max + 1))
        if exclude_recent:
            cutoff = timezone.now() - timedelta(hours=24)
            recent = AdCampaignDelivery.objects.filter(
                sent_at__gte=cutoff).values_list('user_id', flat=True)
            qs = qs.exclude(id__in=recent)
        return qs

    def audience_size(self):
        """Kuniga-1 cheklovisiz mos auditoriya hajmi (admin preview uchun)."""
        return self.audience_queryset(exclude_recent=False).count()

    def send(self):
        """Bildirishnoma yuboradi va yuborilgan haqiqiy sonni qaytaradi.

        `send_to_all=True` bo'lsa — filtrlarga mos BARCHA foydalanuvchiga (random
        va kuniga-1 cheklovisiz). Aks holda auditoriyadan random `target_count`
        kishiga. Idempotent emas — qayta chaqirilsa yana yuboradi (normal rejimda
        kuniga-1 cheklovi ko'pini to'sadi)."""
        from django.utils import timezone
        from notifications.models import notify
        if self.send_to_all:
            # Hammaga: 24-soatlik cheklovni ham chetlab, to'liq auditoriyaga.
            chosen_ids = list(self.audience_queryset(exclude_recent=False)
                              .values_list('id', flat=True))
        else:
            candidates = list(self.audience_queryset(exclude_recent=True)
                              .values_list('id', flat=True))
            import random
            random.shuffle(candidates)
            chosen_ids = candidates[:self.target_count]
        sent = 0
        for uid in chosen_ids:
            user = User.objects.filter(pk=uid).first()
            if not user:
                continue
            try:
                notify(user, f"📣 {self.title}", self.url or '', 'ads')
                AdCampaignDelivery.objects.create(campaign=self, user=user)
                sent += 1
            except Exception:
                pass
        self.sent_count = sent
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['sent_count', 'status', 'sent_at'])
        return sent


class AdCampaignDelivery(models.Model):
    """Reklama kimga, qachon yuborilganini yozadi (kuniga-1 cheklovi + audit)."""
    campaign = models.ForeignKey(AdCampaign, on_delete=models.CASCADE, related_name='deliveries')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ad_deliveries')
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'ad_campaign_deliveries'
        indexes = [
            models.Index(fields=['user', '-sent_at'], name='adcamp_user_sent_idx'),
        ]

    def __str__(self):
        return f'{self.campaign.title} → {self.user}'
