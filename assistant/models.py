"""AI yordamchi — ma'lumotlar modellari.

Ikki guruh:
  1) UnansweredQuery — javobsiz savollar jurnali (mavjud, o'zgarmagan)
  2) Agent modellari — tool-calling agenti uchun (0-to'lqin):
        AgentTask      — uzluksiz vazifa (bir necha gap davomida)
        SelectionSet   — ekranga chiqarilgan ro'yxat (ovoz bilan tanlash uchun)
        PendingAction  — tasdiq kutayotgan amal (LLM yarata oladi, BAJARA olmaydi)
        AgentAuditLog  — har bir tool chaqiruvi (xavfsizlik + debug)
        AgentUsage     — kunlik limit (suiiste'mol himoyasi)
"""

import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class UnansweredQuery(models.Model):
    # Normallashtirilgan kalit — bir xil savollarni birlashtirish (dedupe) uchun.
    normalized = models.CharField(max_length=255, unique=True, verbose_name='Kalit (ichki)')
    text = models.CharField(max_length=1000, verbose_name='Savol')
    count = models.PositiveIntegerField(default=1, verbose_name='Necha marta so‘ralgan')
    resolved = models.BooleanField(default=False, verbose_name='Hal qilingan')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Birinchi marta')
    last_seen = models.DateTimeField(auto_now=True, verbose_name='Oxirgi marta')

    class Meta:
        db_table = 'assistant_unanswered'
        ordering = ['-count', '-last_seen']
        verbose_name = 'Javobsiz savol'
        verbose_name_plural = 'Javobsiz savollar (AI)'

    def __str__(self):
        return f'{self.text} ×{self.count}'


def record_unanswered(text):
    """Tushunilmagan savolni yozadi/hisoblagichini oshiradi. Xatoga chidamli.

    Chat oqimini hech qachon buzmasligi uchun barcha xatoliklar yutiladi
    (chaqiruvchi tomonda ham try/except bor).
    """
    text = (text or '').strip()
    if not text:
        return
    from django.utils import timezone
    from django.db.models import F
    from .engine import _norm
    key = _norm(text)[:255]
    if not key:
        return
    obj, created = UnansweredQuery.objects.get_or_create(
        normalized=key, defaults={'text': text[:1000]})
    if not created:
        UnansweredQuery.objects.filter(pk=obj.pk).update(
            count=F('count') + 1, last_seen=timezone.now())


# ═══════════════════════════════════════════════════════════════════════════
#  AGENT MODELLARI (0-to'lqin)
# ═══════════════════════════════════════════════════════════════════════════

# Muddatlar — env orqali emas, ataylab kodda (xavfsizlik chegarasi).
TASK_TTL_HOURS = 2        # Yarim qolgan vazifa shuncha vaqt "tirik"
SELECTION_TTL_MIN = 30    # Ekrandagi ro'yxat shuncha vaqt tanlanadi
PENDING_TTL_MIN = 30      # Tasdiqlanmagan amal shundan keyin o'ladi


def _token():
    """Qisqa, taxmin qilib bo'lmaydigan ommaviy kalit (URL/ovoz uchun qulay)."""
    return secrets.token_urlsafe(9)


class AgentTask(models.Model):
    """Bajarilayotgan vazifa — bir necha gap davomida saqlanadi.

    Nega kerak: LLM ga butun suhbat tarixini yuborish o'rniga ixcham holat
    yuboriladi. Token 3-4 barobar kam, AI adashmaydi, suhbat uzilsa davom
    ettirish mumkin.
    """

    STATUS_CHOICES = [
        ('active', 'Faol'),
        ('done', 'Tugallangan'),
        ('abandoned', 'Tashlab ketilgan'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='agent_tasks', null=True, blank=True,
    )
    # Anonim (tizimga kirmagan) foydalanuvchi uchun sessiya kaliti.
    session_key = models.CharField(max_length=64, blank=True, db_index=True)

    goal = models.CharField('Maqsad', max_length=40, db_index=True)
    state = models.CharField('Holat', max_length=40, blank=True)
    # To'plangan ma'lumot: {"store_id": 12, "product_id": None, ...}
    slots = models.JSONField('Ma\'lumotlar', default=dict, blank=True)
    # Hali yetishmayotgan maydonlar — AI aynan shularni so'raydi.
    missing = models.JSONField('Yetishmayotgan', default=list, blank=True)
    last_ui_ref = models.CharField(max_length=32, blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES,
                              default='active', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'assistant_agent_task'
        ordering = ['-updated_at']
        verbose_name = 'Agent vazifasi'
        verbose_name_plural = 'Agent vazifalari (AI)'
        indexes = [
            models.Index(fields=['user', 'status', '-updated_at'],
                         name='agent_task_user_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=TASK_TTL_HOURS)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.goal}/{self.state} — {self.user_id or self.session_key}'

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def set_slot(self, key, value):
        """Bitta maydonni yozadi va `missing` ro'yxatidan olib tashlaydi."""
        self.slots = {**(self.slots or {}), key: value}
        if key in (self.missing or []):
            self.missing = [m for m in self.missing if m != key]


class SelectionSet(models.Model):
    """Ekranga chiqarilgan ro'yxat — «anorni tanladim» ni yechish uchun.

    LLM ga har safar 10 ta kartani qayta yuborish qimmat va sekin. O'rniga
    ro'yxat serverda saqlanadi, tanlov ko'p hollarda LLM'siz aniqlanadi.
    """

    ref = models.CharField(primary_key=True, max_length=32, default=_token)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='agent_selections', null=True, blank=True,
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    task = models.ForeignKey(
        AgentTask, on_delete=models.CASCADE, related_name='selections',
        null=True, blank=True,
    )

    section = models.CharField(max_length=24)
    # [{id, index, title, subtitle, aliases: [...], price, distance, rating}, ...]
    items = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'assistant_selection_set'
        ordering = ['-created_at']
        verbose_name = 'Tanlov ro\'yxati'
        verbose_name_plural = 'Tanlov ro\'yxatlari (AI)'

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=SELECTION_TTL_MIN)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.ref} — {self.section} ({len(self.items or [])} ta)'

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class PendingAction(models.Model):
    """Tasdiq kutayotgan amal.

    ⚠️ ARXITEKTURA QOIDASI: LLM bu yozuvni YARATA oladi, lekin BAJARA olmaydi.
    Bajarish faqat foydalanuvchi tasdiqlagandan keyin, alohida endpoint orqali
    bo'ladi. Shu tufayli «model tasdiq so'rashni unutib qo'ydi» degan holat
    umuman mumkin emas — bu prompt emas, arxitektura kafolati.
    """

    STATUS_CHOICES = [
        ('pending', 'Tasdiq kutilmoqda'),
        ('confirmed', 'Tasdiqlangan'),
        ('cancelled', 'Bekor qilingan'),
        ('expired', 'Muddati o\'tgan'),
        ('failed', 'Xatolik'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='agent_pending_actions',
    )
    task = models.ForeignKey(
        AgentTask, on_delete=models.SET_NULL, related_name='pending_actions',
        null=True, blank=True,
    )

    section = models.CharField(max_length=24)
    action = models.CharField(max_length=40)
    # Bajarish uchun kerakli parametrlar (serverda tekshirilgan holda).
    payload = models.JSONField(default=dict)
    # Foydalanuvchiga ko'rsatiladigan tasdiq kartasi (UI direktivasi).
    summary_card = models.JSONField(default=dict, blank=True)
    # Umumiy summa — limit tekshiruvi va audit uchun (0 = pulsiz amal).
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES,
                              default='pending', db_index=True)
    # Bajarish natijasi: {"order_id": "...", "error": "..."}
    result = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'assistant_pending_action'
        ordering = ['-created_at']
        verbose_name = 'Tasdiq kutayotgan amal'
        verbose_name_plural = 'Tasdiq kutayotgan amallar (AI)'
        indexes = [
            models.Index(fields=['user', 'status', '-created_at'],
                         name='pending_user_status_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=PENDING_TTL_MIN)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.section}.{self.action} — {self.amount} ({self.status})'

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_actionable(self):
        """Tasdiqlash mumkinmi — faqat kutilayotgan va muddati o'tmagan."""
        return self.status == 'pending' and not self.is_expired


class AgentAuditLog(models.Model):
    """Har bir tool chaqiruvi — xavfsizlik tekshiruvi va debug uchun.

    Bu jadval tez o'sadi. Eskirtirish: `cleanup_agent_logs` boshqaruv buyrug'i
    (90 kundan eski yozuvlarni o'chiradi).
    """

    RESULT_CHOICES = [
        ('ok', 'Muvaffaqiyat'),
        ('denied', 'Vakolat yo\'q'),
        ('limited', 'Limit oshdi'),
        ('error', 'Xatolik'),
        ('pending', 'Tasdiqqa yuborildi'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='agent_audit_logs', null=True, blank=True,
    )
    session_key = models.CharField(max_length=64, blank=True)
    task_id = models.UUIDField(null=True, blank=True)

    section = models.CharField(max_length=24, db_index=True)
    action = models.CharField(max_length=40, db_index=True)
    params = models.JSONField(default=dict, blank=True)
    result_status = models.CharField(max_length=10, choices=RESULT_CHOICES,
                                     default='ok', db_index=True)
    error = models.CharField(max_length=300, blank=True)

    duration_ms = models.PositiveIntegerField(default=0)
    llm_model = models.CharField(max_length=60, blank=True)
    tokens_in = models.PositiveIntegerField(default=0)
    tokens_out = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'assistant_agent_audit'
        ordering = ['-created_at']
        verbose_name = 'Agent jurnali'
        verbose_name_plural = 'Agent jurnali (AI)'
        indexes = [
            models.Index(fields=['user', '-created_at'], name='agent_audit_user_idx'),
        ]

    def __str__(self):
        return f'{self.section}.{self.action} — {self.result_status}'


class AgentUsage(models.Model):
    """Kunlik limit — buzuq tsikl bir kechada byudjetni yeb qo'ymasligi uchun.

    Limitlar `guard.py` da (LIMITS) belgilanadi, bu yerda faqat hisoblagich.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='agent_usage',
    )
    date = models.DateField(db_index=True)

    llm_calls = models.PositiveIntegerField(default=0)
    tool_calls = models.PositiveIntegerField(default=0)
    # ⚠️ Ikki alohida hisoblagich, ataylab:
    #   proposals — TAKLIF qilingan amal (PendingAction yaratilgan). Arzon,
    #               foydalanuvchi tasdiqlamasligi ham mumkin → chegarasi kengroq.
    #   mutations — HAQIQATDA bajarilgan amal (tasdiqlangan buyurtma/to'lov).
    # Bittasi bilan cheklansa: 20 ta taklif qildirib, bittasini ham tasdiqlamagan
    # odam kun oxirigacha bloklanardi — bu noto'g'ri edi.
    proposals = models.PositiveIntegerField(default=0)
    mutations = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        db_table = 'assistant_agent_usage'
        unique_together = [('user', 'date')]
        ordering = ['-date']
        verbose_name = 'Agent kunlik sarfi'
        verbose_name_plural = 'Agent kunlik sarfi (AI)'

    def __str__(self):
        return f'{self.user} — {self.date}: {self.llm_calls} LLM / {self.tool_calls} tool'
