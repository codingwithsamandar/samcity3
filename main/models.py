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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=15, unique=True, validators=[phone_validator])
    name = models.CharField(max_length=100, blank=True)
    username = models.CharField(max_length=50, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', blank=True, null=True, validators=[validate_file_type])
    avatar_url = models.TextField(blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
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
    contact_facebook = models.CharField(max_length=100, blank=True)
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


class Neighborhood(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'neighborhoods'
        verbose_name = 'Mahalla'
        verbose_name_plural = 'Mahallalar'

    def __str__(self):
        return self.name


class ChatRoom(models.Model):
    neighborhood = models.OneToOneField(Neighborhood, on_delete=models.CASCADE, related_name='chat_room')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_rooms'


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to='chat_images/%Y/%m/', blank=True, null=True)
    file = models.FileField(upload_to='chat_files/%Y/%m/', blank=True, null=True)
    audio = models.FileField(upload_to='chat_voice/%Y/%m/', blank=True, null=True)
    is_admin_message = models.BooleanField(default=False)
    # ── Advanced chat features ───────────────────────────────────────────────
    reply_to = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies',
    )
    forwarded_from = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='forwards',
    )
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [models.Index(fields=['room', 'created_at'], name='chat_msg_room_created_idx')]

    def __str__(self):
        return f'{self.room} — {self.created_at.strftime("%H:%M")}'


class ChatAdmin(models.Model):
    """Mahalla admini — chatda anonim ko'rinadi, faqat mahalla bo'yicha tayinlanadi."""
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


class ChatMember(models.Model):
    """Chat xonasidagi a'zo — tasdiqlangan yoki ban qilingan."""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_memberships')
    is_approved = models.BooleanField(default=False, verbose_name='Tasdiqlangan')
    is_banned = models.BooleanField(default=False, verbose_name='Bloklangan')
    joined_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    # ── Read receipts / presence ─────────────────────────────────────────────
    last_read_at = models.DateTimeField(blank=True, null=True, verbose_name='Oxirgi o\'qilgan vaqt')
    last_seen_at = models.DateTimeField(blank=True, null=True, verbose_name='Oxirgi faollik')

    class Meta:
        db_table = 'chat_members'
        verbose_name = 'Chat a\'zosi'
        verbose_name_plural = 'Chat a\'zolari'
        unique_together = [('room', 'user')]

    def __str__(self):
        status = 'ban' if self.is_banned else ('tasdiqlangan' if self.is_approved else 'kutmoqda')
        return f'{self.room.neighborhood.name} — {self.user} [{status}]'


class MessageReaction(models.Model):
    """Xabarga reaksiya (emoji)."""
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_reactions')
    emoji = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_message_reactions'
        verbose_name = 'Reaksiya'
        verbose_name_plural = 'Reaksiyalar'
        unique_together = [('message', 'user', 'emoji')]

    def __str__(self):
        return f'{self.emoji} — {self.user}'


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
