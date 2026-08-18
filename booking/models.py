import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


VENUE_TYPE_CHOICES = [
    ('wedding', "💍 To'yxona"),
    ('restaurant', '🍽️ Restoran'),
    ('barber', '💈 Sartaroshxona'),
    ('gym', '🏋️ Sport zal'),
    ('cafe', '☕ Kafe'),
    ('beauty', "💅 Go'zallik saloni"),
    ('clinic', '🏥 Klinika'),
    ('other', '📍 Boshqa'),
]

# Vaqt-slot (usta/shifokor tanlanadigan) turlari — sartarosh, salon, restoran,
# kafe va klinika. Klinikada «usta» = shifokor, «xizmat» = qabul turi.
SLOT_TYPES = ('barber', 'beauty', 'restaurant', 'cafe', 'clinic')
# Maksimal bekor-qilish jarimasi (foiz). Joy egasi bundan oshira olmaydi.
MAX_PENALTY_PERCENT = 15
# Bron oldindan qancha kunga ochiq. Mijoz bugundan boshlab shu oraliqdagi
# sanalarni band qila oladi (bugun + 7 kun). Undan narisi — rad etiladi:
# uzoq kelajakka qilingan bronlar odatda kelib chiqmaydi va slotni band qiladi.
MAX_BOOKING_AHEAD_DAYS = 7

# Klinikada bemor qabulga odatda ancha oldindan yoziladi (shifokor jadvali
# haftalab oldin to'ladi) — 7 kun kam, shuning uchun oyna kengroq.
CLINIC_BOOKING_AHEAD_DAYS = 30

# Tur bo'yicha alohida oyna; ro'yxatda yo'q turlar MAX_BOOKING_AHEAD_DAYS oladi.
AHEAD_DAYS_BY_TYPE = {'clinic': CLINIC_BOOKING_AHEAD_DAYS}


def booking_ahead_days(venue=None):
    """Shu joy uchun bron necha kun oldindan ochiq (venue berilmasa — umumiy)."""
    if venue is None:
        return MAX_BOOKING_AHEAD_DAYS
    return AHEAD_DAYS_BY_TYPE.get(venue.venue_type, MAX_BOOKING_AHEAD_DAYS)


def booking_window(venue=None):
    """Bron ochiq bo'lgan sana oralig'i: (birinchi_kun, oxirgi_kun)."""
    today = timezone.localdate()
    return today, today + timedelta(days=booking_ahead_days(venue))


def booking_date_error(value, venue=None):
    """Sana oynadan tashqarida bo'lsa xato MATNI, aks holda None.

    Yagona manba — veb forma ham, API ham shuni chaqiradi, shunda ikki
    joyda ikki xil qoida paydo bo'lmaydi. `venue` berilsa oyna o'sha
    joyning turiga qarab olinadi (klinika — kengroq).
    """
    if value is None:
        return "Iltimos, sanani tanlang."
    first, last = booking_window(venue)
    if value < first:
        return "O'tgan sanaga bron qilib bo'lmaydi."
    if value > last:
        return (f"Bron faqat {booking_ahead_days(venue)} kun oldindan ochiq — "
                f"{last.strftime('%d.%m.%Y')} gacha bo'lgan sanani tanlang.")
    return None


# Bitta joy uchun portfoliodagi maksimal ish soni — sahifa og'irlashib
# ketmasligi uchun (galereya bir sahifada to'liq yuklanadi).
MAX_WORKS_PER_VENUE = 30


class Venue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='venues',
    )
    name = models.CharField(max_length=200, verbose_name='Nomi')
    venue_type = models.CharField(
        max_length=20, choices=VENUE_TYPE_CHOICES, default='other',
        db_index=True, verbose_name='Turi',
    )
    description = models.TextField(blank=True, verbose_name='Tavsif')
    address = models.CharField(max_length=300, blank=True, verbose_name='Manzil')
    phone = models.CharField(max_length=30, blank=True, verbose_name='Telefon')
    image = models.ImageField(upload_to='venues/%Y/%m/', blank=True, null=True)
    # Xaritadagi joy (places.Place) bilan bog'lanish. Bog'lansa — o'sha
    # joyning menyusi bron sahifasida ham ko'rinadi, ya'ni restoran menyuni
    # BIR marta kiritadi, mijoz uni ikkala sahifada ham ko'radi.
    place = models.ForeignKey(
        'places.Place', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='venues', verbose_name='Xaritadagi joy')
    capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name="Sig'imi (kishi)")
    price_per_day = models.BigIntegerField(null=True, blank=True, verbose_name="Narx (kunlik, so'm)")
    price_per_hour = models.BigIntegerField(null=True, blank=True, verbose_name="Narx (soatlik, so'm)")
    working_hours_start = models.TimeField(null=True, blank=True, verbose_name='Ish boshlanishi')
    working_hours_end = models.TimeField(null=True, blank=True, verbose_name='Ish tugashi')

    # ── Joylashuv (xaritada ko'rsatish uchun) ────────────────────────────────
    latitude = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)], verbose_name='Kenglik')
    longitude = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)], verbose_name='Uzunlik')

    # ── To'lov / bekor qilish siyosati ───────────────────────────────────────
    prepay_required = models.BooleanField(
        default=True, verbose_name='Oldindan to\'lov majburiy')
    cancel_penalty_percent = models.PositiveSmallIntegerField(
        default=10, validators=[MaxValueValidator(MAX_PENALTY_PERCENT)],
        verbose_name='Bekor qilish jarimasi (%)',
        help_text=f'Bekor qilinsa yoki kelmasa ushlab qolinadigan foiz (max {MAX_PENALTY_PERCENT}%).')
    grace_minutes = models.PositiveSmallIntegerField(
        default=15, verbose_name='Kutish vaqti (daqiqa)',
        help_text='Belgilangan vaqtdan keyin shu daqiqa kutiladi, kelmasa "kelmadi" bo\'ladi.')

    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'venues'
        verbose_name = 'Joy (venue)'
        verbose_name_plural = 'Joylar (venues)'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_venue_type_display()})'

    @property
    def menu_items(self):
        """Bog'langan xaritadagi joyning faol menyusi (bog'lanmasa — bo'sh)."""
        if not self.place_id:
            return []
        return list(self.place.menu_items.filter(is_active=True))

    @property
    def uses_slots(self):
        """Vaqt-slot va usta tanlanadigan joymi (SLOT_TYPES bo'yicha)."""
        return self.venue_type in SLOT_TYPES

    @property
    def staff_label(self):
        """Xodim uchun joyga mos so'z: klinikada «Shifokor», aks holda «Usta»."""
        return 'Shifokor' if self.venue_type == 'clinic' else 'Usta'

    @property
    def penalty_percent(self):
        return min(self.cancel_penalty_percent or 0, MAX_PENALTY_PERCENT)

    def active_staff(self):
        return list(self.staff.filter(is_active=True))

    def _day_time_off_by_staff(self, date):
        """Kun bo'yi barcha yopilgan vaqtlarni BIR so'rovda, usta bo'yicha."""
        from collections import defaultdict
        by_staff = defaultdict(list)
        for off in StaffTimeOff.objects.filter(staff__venue=self, date=date):
            by_staff[off.staff_id].append(off)
        return by_staff

    def _day_bookings_by_staff(self, date):
        """Kun bo'yi barcha faol bronlarni BIR so'rovda yuklab, usta bo'yicha guruhlaydi.

        DIQQAT: .only('staff_id', ...) ISHLATILMAYDI — u staff_id'ni deferred qilib,
        har bron uchun qo'shimcha so'rovga (N+1) sabab bo'lardi. To'liq obyekt
        bitta so'rovda yuklanadi.
        """
        from collections import defaultdict
        by_staff = defaultdict(list)
        rows = self.bookings.filter(
            booking_date=date, status__in=('pending', 'confirmed'),
        )
        for b in rows:
            by_staff[b.staff_id].append(b)
        return by_staff

    def free_staff_at(self, date, start, duration_minutes=30):
        """Shu sana/vaqtда bo'sh ustalar ro'yxati (N+1siz — bir so'rov)."""
        by_staff = self._day_bookings_by_staff(date)
        off_by_staff = self._day_time_off_by_staff(date)
        return [s for s in self.active_staff()
                if s.is_free_at(date, start, duration_minutes,
                                bookings=by_staff.get(s.id, []),
                                time_off=off_by_staff.get(s.id, []))]

    def available_slots(self, date, staff=None, duration_minutes=30):
        """Berilgan sana uchun bo'sh vaqt-slotlar ro'yxati ('HH:MM').

        - staff berilsa: faqat o'sha ustaning bo'sh vaqtlari.
        - ustalar bor (staff=None): kamida bitta usta bo'sh bo'lgan vaqtlar.
        - ustalar yo'q: joy darajasida band bo'lmagan vaqtlar.
        O'tib ketgan vaqtlar (bugun uchun) chiqariladi.
        """
        start_t = self.working_hours_start or datetime.strptime('09:00', '%H:%M').time()
        end_t = self.working_hours_end or datetime.strptime('20:00', '%H:%M').time()
        step = max(int(duration_minutes or 30), 10)
        base = datetime.combine(date, start_t)
        end_dt = datetime.combine(date, end_t)
        now = timezone.localtime()
        staff_list = self.active_staff()

        # Kun bronlarini BIR marta yuklaymiz (N+1 oldini olish: ilgari
        # har usta×har slot uchun alohida so'rov bo'lardi).
        by_staff = self._day_bookings_by_staff(date)
        off_by_staff = self._day_time_off_by_staff(date)
        all_day = [b for lst in by_staff.values() for b in lst]

        # Joy darajasidagi bandlik (usta yo'q holat uchun)
        venue_taken = {b.start_time.strftime('%H:%M') for b in all_day if b.start_time}

        slots = []
        cur = base
        while cur + timedelta(minutes=step) <= end_dt:
            label = cur.strftime('%H:%M')
            t = cur.time()
            is_past = (date == now.date() and t <= now.time())
            if not is_past:
                if staff is not None:
                    free = staff.is_free_at(
                        date, t, step, bookings=by_staff.get(staff.id, []),
                        time_off=off_by_staff.get(staff.id, []))
                elif staff_list:
                    free = any(s.is_free_at(
                        date, t, step, bookings=by_staff.get(s.id, []),
                        time_off=off_by_staff.get(s.id, [])) for s in staff_list)
                else:
                    free = label not in venue_taken
                if free:
                    slots.append(label)
            cur += timedelta(minutes=step)
        return slots


class VenueService(models.Model):
    """Joyning xizmati (masalan: 'Soch olish' — 30 000 so'm, 30 daqiqa)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=150, verbose_name='Xizmat nomi')
    description = models.TextField(blank=True, verbose_name='Xizmat haqida')
    image = models.ImageField(
        upload_to='venues/services/%Y/%m/', blank=True, null=True, verbose_name='Rasm')
    price = models.BigIntegerField(verbose_name="Narx (so'm)")
    duration_minutes = models.PositiveIntegerField(
        default=30, verbose_name='Davomiyligi (daqiqa)')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'venue_services'
        verbose_name = 'Xizmat'
        verbose_name_plural = 'Xizmatlar'
        ordering = ['order', 'price']

    def __str__(self):
        return f'{self.name} — {self.price} so\'m'


class VenueStaff(models.Model):
    """Joyning ishchisi/ustasi (sartarosh, master va h.k.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='staff')
    # Usta hisobi. Ilgari usta shunchaki egasi kiritgan ism edi — u tizimga
    # kira olmasdi va o'z jadvalini ko'ra olmasdi. Bog'lansa, usta o'z
    # panelini ochadi (FAQAT o'ziga biriktirilgan bronlar).
    # FK, OneToOne emas: bir odam ikki joyda usta bo'lishi mumkin.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='staff_roles', verbose_name='Hisob (panelga kirish uchun)')
    name = models.CharField(max_length=120, verbose_name='Ism')
    phone = models.CharField(
        max_length=30, blank=True, verbose_name='Telefon',
        help_text='Shu raqamli foydalanuvchi topilsa, ustaga panel ochiladi.')
    specialty = models.CharField(max_length=120, blank=True, verbose_name='Mutaxassisligi')
    photo = models.ImageField(upload_to='venues/staff/%Y/%m/', blank=True, null=True)
    bio = models.TextField(blank=True, verbose_name='Usta haqida')
    experience_years = models.PositiveSmallIntegerField(default=0, verbose_name='Tajriba (yil)')
    rating = models.FloatField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(5)], verbose_name='Baho')
    reviews_count = models.PositiveIntegerField(default=0, verbose_name='Sharhlar soni')
    completed_count = models.PositiveIntegerField(default=0, verbose_name='Bajarilgan ishlar')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'venue_staff'
        verbose_name = 'Ishchi / usta'
        verbose_name_plural = 'Ishchilar / ustalar'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def link_user_by_phone(self):
        """Telefon raqami bo'yicha hisobni topib bog'laydi (topilmasa — None).

        Egasi ustani qo'shganda chaqiriladi: usta allaqachon ro'yxatdan
        o'tgan bo'lsa, paneli darhol ochiladi.
        """
        if self.user_id or not self.phone:
            return None
        from main.models import User
        digits = ''.join(ch for ch in self.phone if ch.isdigit())[-9:]
        if len(digits) < 9:
            return None
        found = User.objects.filter(phone__endswith=digits).first()
        if found:
            self.user = found
            self.save(update_fields=['user'])
        return found

    def is_free_at(self, date, start, duration_minutes=30, bookings=None,
                   time_off=None):
        """Berilgan sana/vaqtда usta bo'shmi.

        Ikki sabab band qiladi: mavjud BRON va ustaning o'zi YOPGAN vaqti
        (tushlik, dam olish, shaxsiy ish — `StaffTimeOff`).

        `bookings` / `time_off` berilsa — DB so'rovi o'rniga shu ro'yxatlar
        ishlatiladi (N+1 oldini olish: chaqiruvchi kun ma'lumotini bir
        marta yuklaydi).
        """
        if not start:
            return True

        from datetime import datetime as _d, timedelta as _t
        end_new = (_d.combine(date, start) + _t(minutes=duration_minutes)).time()

        if time_off is None:
            time_off = self.time_off.filter(date=date)
        for off in time_off:
            if off.start_time is None:          # kun bo'yi yopiq
                return False
            off_end = off.end_time or off.start_time
            if start < off_end and off.start_time < end_new:
                return False
        from datetime import datetime as _dt, timedelta as _td
        new_end = (_dt.combine(date, start) + _td(minutes=duration_minutes)).time()
        if bookings is None:
            bookings = self.bookings.filter(
                booking_date=date, status__in=('pending', 'confirmed'))
        for b in bookings:
            if not b.start_time:
                continue
            b_end = b.end_time or b.start_time
            if start < b_end and b.start_time < new_end:
                return False
        return True


class VenueWork(models.Model):
    """Joy egasining portfoliosi — qilgan ishi rasmi va ma'lumoti.

    Masalan sartaroshxona: "Fade soch turmagi" rasmi, qaysi usta qilgani,
    qaysi xizmatga tegishli va narxi. Mijoz bron qilishdan oldin ko'radi.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='works')
    title = models.CharField(max_length=150, verbose_name='Ish nomi')
    description = models.TextField(blank=True, verbose_name='Tavsif')
    image = models.ImageField(upload_to='venues/works/%Y/%m/', verbose_name='Rasm')
    service = models.ForeignKey(
        VenueService, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='works', verbose_name='Xizmat')
    staff = models.ForeignKey(
        VenueStaff, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='works', verbose_name='Usta/ishchi')
    price = models.BigIntegerField(null=True, blank=True, verbose_name="Narx (so'm)")
    is_active = models.BooleanField(default=True, verbose_name="Ko'rsatilsin")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'venue_works'
        verbose_name = 'Bajarilgan ish'
        verbose_name_plural = 'Bajarilgan ishlar'
        ordering = ['order', '-created_at']

    def __str__(self):
        return f'{self.venue.name} — {self.title}'



class StaffTimeOff(models.Model):
    """Usta yopgan vaqt — tushlik, dam olish, shaxsiy ish.

    Nega kerak: ilgari ustaning vaqti faqat BRON bilan band bo'lardi va usta
    o'zi "bu vaqtda yo'qman" deya olmasdi — mijoz istalgan bo'sh slotga
    yozilaverardi. Endi usta o'z jadvalini boshqaradi.

    `start_time` bo'sh bo'lsa — butun kun yopiq.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey(
        VenueStaff, on_delete=models.CASCADE, related_name='time_off')
    date = models.DateField(db_index=True, verbose_name='Sana')
    start_time = models.TimeField(
        null=True, blank=True, verbose_name='Boshlanish',
        help_text="Bo'sh qoldirilsa \u2014 butun kun yopiq.")
    end_time = models.TimeField(null=True, blank=True, verbose_name='Tugash')
    reason = models.CharField(max_length=120, blank=True, verbose_name='Sabab')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'venue_staff_time_off'
        verbose_name = 'Usta yopgan vaqt'
        verbose_name_plural = 'Usta yopgan vaqtlar'
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['staff', 'date'], name='stf_off_staff_date_idx'),
        ]

    def __str__(self):
        if self.start_time is None:
            return f'{self.staff.name} \u2014 {self.date} (butun kun)'
        return f'{self.staff.name} \u2014 {self.date} {self.start_time:%H:%M}'

    @property
    def whole_day(self):
        return self.start_time is None


class VenueBooking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),          # yaratildi, to'lov kutilmoqda
        ('confirmed', 'Tasdiqlangan'),      # to'langan
        ('completed', 'Yakunlangan'),       # xizmat ko'rsatildi
        ('cancelled', 'Bekor qilingan'),    # foydalanuvchi bekor qildi
        ('no_show', 'Kelmadi'),             # belgilangan vaqtda kelmadi
    ]
    EVENT_TYPE_CHOICES = [
        ('wedding', "To'y"),
        ('birthday', "Tug'ilgan kun"),
        ('engagement', 'Unashtiruv (Fotiha)'),
        ('other', 'Boshqa'),
    ]
    SUBSCRIPTION_TYPE_CHOICES = [
        ('daily', 'Kunlik'),
        ('monthly', 'Oylik'),
        ('yearly', 'Yillik'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='venue_bookings',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True,
    )

    # ── Xizmat / usta (sartarosh, salon, restoran...) ────────────────────────
    service = models.ForeignKey(
        VenueService, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bookings', verbose_name='Xizmat')
    staff = models.ForeignKey(
        VenueStaff, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bookings', verbose_name='Usta/ishchi')

    # ── Umumiy maydonlar ─────────────────────────────────────────────────────
    booking_date = models.DateField(verbose_name='Sana')
    start_time = models.TimeField(null=True, blank=True, verbose_name='Boshlanish vaqti')
    end_time = models.TimeField(null=True, blank=True, verbose_name='Tugash vaqti')
    guests = models.PositiveIntegerField(default=1, verbose_name='Mehmonlar soni')
    message = models.TextField(blank=True, verbose_name='Xabar')
    total_amount = models.BigIntegerField(null=True, blank=True, verbose_name="Umumiy summa (so'm)")
    created_at = models.DateTimeField(auto_now_add=True)

    # ── To'lov / jarima ──────────────────────────────────────────────────────
    paid_amount = models.BigIntegerField(default=0, verbose_name="To'langan summa")
    penalty_amount = models.BigIntegerField(default=0, verbose_name='Ushlab qolingan jarima')
    refund_amount = models.BigIntegerField(default=0, verbose_name='Qaytariladigan summa')
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # ── Haqiqiy bajarilish vaqti (taxmin uchun o'lchov) ────────────
    # Usta "Yakunlandi" bosganda to'ldiriladi. Shu ma'lumot yig'ilgach,
    # "bu usta bu xizmatni odatda necha daqiqada bajaradi" degan TAXMIN
    # rejadagi `duration_minutes` o'rniga haqiqatga tayanadi.
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name='Yakunlangan vaqt')
    actual_minutes = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='Haqiqiy davomiylik (daqiqa)',
        help_text='Yakunlanganda hisoblanadi — taxminiy vaqtni aniqlashtiradi.')

    # ── Eslatma (send_booking_reminders buyrug'i to'ldiradi) ─────────────────
    reminder_sent_at = models.DateTimeField(
        null=True, blank=True, verbose_name='Eslatma yuborilgan vaqt',
    )

    # ── To'yxona (wedding) ───────────────────────────────────────────────────
    event_type = models.CharField(
        max_length=20, choices=EVENT_TYPE_CHOICES, blank=True, verbose_name='Tadbir turi',
    )
    decoration_needed = models.BooleanField(default=False, verbose_name='Bezatish kerak')

    # ── Sartarosh / Salon — eski matnli maydonlar (moslik uchun saqlandi) ────
    master_name = models.CharField(max_length=120, blank=True, verbose_name='Usta ismi')
    service_type = models.CharField(max_length=120, blank=True, verbose_name='Xizmat turi')

    # ── Restoran / Cafe ──────────────────────────────────────────────────────
    table_count = models.PositiveIntegerField(default=1, verbose_name='Stollar soni')
    special_request = models.TextField(blank=True, verbose_name='Maxsus talab')

    # ── Sport zal (gym) ──────────────────────────────────────────────────────
    subscription_type = models.CharField(
        max_length=20, choices=SUBSCRIPTION_TYPE_CHOICES, blank=True, verbose_name='Obuna turi',
    )

    class Meta:
        db_table = 'venue_bookings'
        verbose_name = 'Bron'
        verbose_name_plural = 'Bronlar'
        ordering = ['-created_at']
        indexes = [
            # Slot bo'shligi/usta band-bo'shligi har sahifada so'raladi.
            models.Index(fields=['staff', 'booking_date'], name='vb_staff_date_idx'),
            models.Index(fields=['venue', 'booking_date'], name='vb_venue_date_idx'),
            models.Index(fields=['user', '-created_at'], name='vb_user_created_idx'),
        ]

    def __str__(self):
        return f'{self.venue.name} — {self.booking_date} ({self.get_status_display()})'

    # ── Holat yordamchilari ──────────────────────────────────────────────────
    @property
    def is_paid(self):
        return self.paid_amount and self.paid_amount > 0

    @property
    def payment_state(self):
        """To'lov holati — usta/egasi paneli uchun: ('kod', 'matn').

        Uch holat farqlanadi: to'langan; oldindan to'lov MAJBURIY-yu hali
        to'lanmagan (xavfli — mijoz kelmasligi mumkin); oldindan to'lov
        talab qilinmaydi, ya'ni joyida to'laydi.
        """
        if self.is_paid:
            return ('paid', "To'langan")
        if self.venue.prepay_required:
            return ('awaiting', "To'lov kutilmoqda")
        return ('onsite', "Joyida to'laydi")

    @property
    def amount_due(self):
        """Hali to'lanmagan summa (so'm)."""
        return max((self.total_amount or 0) - (self.paid_amount or 0), 0)

    @property
    def starts_at(self):
        """Bron boshlanish vaqti (datetime) — no-show hisobi uchun."""
        if not self.start_time:
            return None
        return timezone.make_aware(datetime.combine(self.booking_date, self.start_time))

    def computed_penalty(self):
        """To'langan summadan ushlab qolinadigan jarima (so'm)."""
        if not self.is_paid:
            return 0
        return int(self.paid_amount * self.venue.penalty_percent / 100)

    def mark_completed(self):
        """Xizmat yakunlandi — haqiqiy davomiylikni ham o'lchab qo'yamiz.

        Davomiylik rejalashtirilgan boshlanishdan yakunlashgacha. Bu aniq
        o'lchov emas (usta kechikib bosishi mumkin), shuning uchun keyin
        MEDIANA olinadi — bitta unutilgan yozuv o'rtachani buzmasin.
        """
        now = timezone.now()
        self.completed_at = now
        started = self.starts_at
        if started:
            mins = int((now - started).total_seconds() // 60)
            # Manfiy (erta bosilgan) yoki bir kunlik (unutilgan) qiymatlar
            # o'lchov sifatida yaroqsiz — yozilmaydi.
            if 0 < mins <= 8 * 60:
                self.actual_minutes = mins
        self.status = 'completed'
        self.save(update_fields=['status', 'completed_at', 'actual_minutes'])

    def mark_cancelled(self):
        """Foydalanuvchi bekor qildi — jarima ushlanadi, qolgani qaytariladi."""
        if self.is_paid:
            self.penalty_amount = self.computed_penalty()
            self.refund_amount = self.paid_amount - self.penalty_amount
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.save(update_fields=['status', 'penalty_amount', 'refund_amount', 'cancelled_at'])

    def mark_no_show(self):
        """Belgilangan vaqtda kelmadi — jarima ushlanadi."""
        if self.is_paid:
            self.penalty_amount = self.computed_penalty()
            self.refund_amount = self.paid_amount - self.penalty_amount
        self.status = 'no_show'
        self.cancelled_at = timezone.now()
        self.save(update_fields=['status', 'penalty_amount', 'refund_amount', 'cancelled_at'])
