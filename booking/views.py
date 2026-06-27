from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_POST

from main.utils import validate_file_type
from .models import (
    Venue, VenueBooking, VenueService, VenueStaff,
    VENUE_TYPE_CHOICES, SLOT_TYPES, MAX_PENALTY_PERCENT,
)


def _parse_time(value):
    """'HH:MM' satrini time obyektiga aylantiradi, bo'sh bo'lsa None."""
    value = (value or '').strip()
    if not value:
        return None
    for fmt in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


WHOLE_DAY_TYPES = ('wedding', 'other')
TIME_SLOT_TYPES = ('barber', 'beauty', 'restaurant', 'cafe')
ACTIVE_BOOKING_STATUSES = ('pending', 'confirmed')


def _booking_conflict(venue, booking_date, start, end, exclude_id=None, staff=None):
    """Bron to'qnashuvini tekshiradi. To'qnashuv bo'lsa True qaytaradi.

    staff berilsa — faqat o'sha ustaning o'sha sana/vaqtdagi bandligini tekshiradi
    (turli ustalar bir vaqtda band bo'lishi mumkin).
    """
    qs = VenueBooking.objects.filter(
        venue=venue, booking_date=booking_date, status__in=ACTIVE_BOOKING_STATUSES,
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    if staff is not None:
        qs = qs.filter(staff=staff)

    vt = venue.venue_type
    if vt in WHOLE_DAY_TYPES:
        # Butun kunlik joy — bir kunga bitta bron
        return qs.exists()
    if vt in TIME_SLOT_TYPES and start:
        # Vaqt oralig'i bo'yicha to'qnashuv
        for b in qs:
            if not b.start_time:
                continue
            b_end = b.end_time or b.start_time
            new_end = end or start
            # oraliqlar kesishsa
            if start < b_end and b.start_time < new_end:
                return True
            if start == b.start_time:
                return True
        return False
    # gym (obuna) va vaqt berilmagan holatlar — to'qnashuv yo'q
    return False


# ─────────────────────────────────────────────────────────────────────────────
#  Venue ro'yxati (login shart emas)
# ─────────────────────────────────────────────────────────────────────────────
def venue_list(request):
    vtype = request.GET.get('type', '').strip()
    venues = Venue.objects.filter(is_active=True)
    if vtype:
        venues = venues.filter(venue_type=vtype)
    return render(request, 'booking/venue_list.html', {
        'venues': venues,
        'venue_types': VENUE_TYPE_CHOICES,
        'current_type': vtype,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Venue batafsil + mavjud sanalar
# ─────────────────────────────────────────────────────────────────────────────
def venue_detail(request, pk):
    venue = get_object_or_404(Venue, pk=pk, is_active=True)
    # Band qilingan sanalar (kelgusi, faol bronlar)
    booked = (
        venue.bookings
        .filter(status__in=['pending', 'confirmed'], booking_date__gte=timezone.now().date())
        .values_list('booking_date', flat=True)
    )
    booked_dates = sorted(set(booked))
    return render(request, 'booking/venue_detail.html', {
        'venue': venue,
        'booked_dates': booked_dates,
        'services': venue.services.filter(is_active=True),
        'staff': venue.staff.filter(is_active=True),
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Bron qilish (login kerak) — venue_type ga qarab forma
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='/login/')
def venue_book(request, pk):
    venue = get_object_or_404(Venue, pk=pk, is_active=True)
    services = venue.services.filter(is_active=True)
    staff = venue.staff.filter(is_active=True)
    ctx = {'venue': venue, 'services': services, 'staff': staff}

    if request.method == 'POST':
        booking_date = request.POST.get('booking_date')
        if not booking_date:
            messages.error(request, "Iltimos, sanani tanlang.")
            return render(request, 'booking/venue_book.html', ctx)

        def _int(name, default=None):
            try:
                return int(request.POST.get(name))
            except (TypeError, ValueError):
                return default

        vt = venue.venue_type
        start = _parse_time(request.POST.get('start_time'))
        end = _parse_time(request.POST.get('end_time'))

        # ── Xizmat & usta (slot turlari uchun) ───────────────────────────────
        service = venue.services.filter(pk=request.POST.get('service'), is_active=True).first() \
            if request.POST.get('service') else None
        staff_obj = venue.staff.filter(pk=request.POST.get('staff'), is_active=True).first() \
            if request.POST.get('staff') else None

        if venue.uses_slots:
            if service is None:
                messages.error(request, "Iltimos, xizmatni tanlang.")
                return render(request, 'booking/venue_book.html', ctx)
            if start is None:
                messages.error(request, "Iltimos, vaqtni tanlang.")
                return render(request, 'booking/venue_book.html', ctx)
            # Tugash vaqti = boshlanish + xizmat davomiyligi
            from datetime import date as _date, timedelta
            end = (datetime.combine(_date.today(), start)
                   + timedelta(minutes=service.duration_minutes)).time()

        # ── To'qnashuv (slot turlarida usta bo'yicha) ────────────────────────
        if _booking_conflict(venue, booking_date, start, end,
                             staff=staff_obj if venue.uses_slots else None):
            messages.error(request, "⚠️ Bu vaqt allaqachon band. Boshqa vaqt yoki usta tanlang.")
            return render(request, 'booking/venue_book.html', ctx)

        booking = VenueBooking(
            venue=venue, user=request.user, status='pending',
            booking_date=booking_date, start_time=start, end_time=end,
            service=service, staff=staff_obj,
            guests=_int('guests', 1) or 1,
            message=request.POST.get('message', '').strip(),
        )
        if vt == 'wedding':
            booking.event_type = request.POST.get('event_type', '')
            booking.decoration_needed = 'decoration_needed' in request.POST
        elif vt in ('restaurant', 'cafe'):
            booking.table_count = _int('table_count', 1) or 1
            booking.special_request = request.POST.get('special_request', '').strip()
        elif vt == 'gym':
            booking.subscription_type = request.POST.get('subscription_type', '')
        if service:
            booking.service_type = service.name
        if staff_obj:
            booking.master_name = staff_obj.name

        booking.total_amount = _estimate_total(venue, booking)
        booking.save()

        # Oldindan to'lov majburiy bo'lsa — to'lov sahifasiga
        if venue.prepay_required and booking.total_amount:
            messages.info(request, "Bron yaratildi. Tasdiqlash uchun to'lovni amalga oshiring.")
            return redirect('booking_pay', booking_id=booking.pk)
        messages.success(request, "Bron yaratildi! ✅")
        return redirect('my_venue_bookings')

    return render(request, 'booking/venue_book.html', ctx)


def _estimate_total(venue, booking):
    """Bron summasi — xizmat tanlangan bo'lsa uning narxi, aks holda joy narxi."""
    if booking.service_id:
        svc = booking.service
        if svc:
            return int(svc.price)
    vt = venue.venue_type
    if vt == 'gym':
        return venue.price_per_day or venue.price_per_hour or 0
    if vt in SLOT_TYPES:
        if venue.price_per_hour and booking.start_time and booking.end_time:
            hours = max(1, booking.end_time.hour - booking.start_time.hour)
            return venue.price_per_hour * hours
        return venue.price_per_hour or venue.price_per_day or 0
    return venue.price_per_day or venue.price_per_hour or 0


# ─────────────────────────────────────────────────────────────────────────────
#  Foydalanuvchining bronlari
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='/login/')
def my_bookings(request):
    bookings = (
        VenueBooking.objects.filter(user=request.user)
        .select_related('venue').order_by('-created_at')
    )
    return render(request, 'booking/my_bookings.html', {'bookings': bookings})


# ─────────────────────────────────────────────────────────────────────────────
#  Egasi paneli — o'z venue'laridagi bronlar
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='/login/')
def manage_bookings(request):
    bookings = (
        VenueBooking.objects.filter(venue__owner=request.user)
        .select_related('venue', 'user').order_by('-created_at')
    )
    pending = [b for b in bookings if b.status == 'pending']
    others = [b for b in bookings if b.status != 'pending']
    return render(request, 'booking/manage_bookings.html', {
        'pending': pending,
        'others': others,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Egasi bronni tasdiqlaydi / bekor qiladi / yakunlaydi (POST)
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='/login/')
def booking_action(request, booking_id, action):
    booking = get_object_or_404(VenueBooking, pk=booking_id)
    if booking.venue.owner_id != request.user.id:
        messages.error(request, "Bu amalga ruxsatingiz yo'q.")
        return redirect('manage_bookings')

    if request.method != 'POST':
        return redirect('manage_bookings')

    mapping = {
        'confirm': ('confirmed', "Bron tasdiqlandi. ✅"),
        'cancel': ('cancelled', "Bron bekor qilindi."),
        'complete': ('completed', "Bron yakunlandi."),
    }
    if action in mapping:
        status, msg = mapping[action]
        booking.status = status
        booking.save(update_fields=['status'])
        messages.success(request, msg)
    else:
        messages.error(request, "Noma'lum amal.")

    return redirect('manage_bookings')


# ─────────────────────────────────────────────────────────────────────────────
#  Yangi venue qo'shish (login kerak)
# ─────────────────────────────────────────────────────────────────────────────
def _apply_venue_fields(request, venue):
    """POST dan venue maydonlarini yozadi (create va edit uchun umumiy)."""
    def _vint(name, default=None):
        try:
            return int(str(request.POST.get(name)).replace(' ', ''))
        except (TypeError, ValueError):
            return default

    venue.name = request.POST.get('name', '').strip() or venue.name
    venue.venue_type = request.POST.get('venue_type', venue.venue_type or 'other')
    venue.description = request.POST.get('description', '').strip()
    venue.address = request.POST.get('address', '').strip()
    venue.phone = request.POST.get('phone', '').strip()
    venue.capacity = _vint('capacity')
    venue.price_per_day = _vint('price_per_day')
    venue.price_per_hour = _vint('price_per_hour')
    venue.working_hours_start = request.POST.get('working_hours_start') or None
    venue.working_hours_end = request.POST.get('working_hours_end') or None

    # Joylashuv (xarita uchun)
    def _vfloat(name):
        try:
            return float(str(request.POST.get(name)).replace(',', '.'))
        except (TypeError, ValueError):
            return None
    venue.latitude = _vfloat('latitude')
    venue.longitude = _vfloat('longitude')

    # To'lov / bekor qilish siyosati
    venue.prepay_required = 'prepay_required' in request.POST
    pct = _vint('cancel_penalty_percent', 10) or 0
    venue.cancel_penalty_percent = min(max(pct, 0), MAX_PENALTY_PERCENT)  # 0..15
    venue.grace_minutes = _vint('grace_minutes', 15) or 15

    venue_image = request.FILES.get('image')
    if venue_image:
        try:
            validate_file_type(venue_image)
            venue.image = venue_image
        except Exception as e:
            messages.error(request, f"Rasm: {str(e)}")
    venue.save()


@login_required(login_url='/login/')
def venue_create(request):
    if request.method == 'POST':
        if not request.POST.get('name', '').strip():
            messages.error(request, "Joy nomi majburiy.")
            return render(request, 'booking/venue_create.html', {'venue_types': VENUE_TYPE_CHOICES})
        venue = Venue(owner=request.user, is_active=True)
        _apply_venue_fields(request, venue)
        # Joy ochgan foydalanuvchi avtomatik 'business' roliga o'tadi
        if request.user.role == 'user':
            request.user.role = 'business'
            request.user.save(update_fields=['role'])
        messages.success(request, "Joy muvaffaqiyatli qo'shildi! ✅")
        return redirect('venue_detail', pk=venue.pk)

    return render(request, 'booking/venue_create.html', {'venue_types': VENUE_TYPE_CHOICES})


@login_required(login_url='/login/')
def venue_edit(request, pk):
    venue = get_object_or_404(Venue, pk=pk)
    if venue.owner_id != request.user.id:
        messages.error(request, "Bu joyni tahrirlash huquqingiz yo'q.")
        return redirect('venue_detail', pk=pk)

    if request.method == 'POST':
        if not request.POST.get('name', '').strip():
            messages.error(request, "Joy nomi majburiy.")
        else:
            venue.is_active = 'is_active' in request.POST
            _apply_venue_fields(request, venue)
            messages.success(request, "Joy yangilandi. ✅")
            return redirect('venue_detail', pk=venue.pk)

    return render(request, 'booking/venue_create.html', {
        'venue_types': VENUE_TYPE_CHOICES, 'venue': venue, 'mode': 'edit',
    })


@login_required(login_url='/login/')
def venue_delete(request, pk):
    venue = get_object_or_404(Venue, pk=pk, owner=request.user)
    if request.method == 'POST':
        venue.delete()
        messages.success(request, "Joy o'chirildi.")
        return redirect('venue_list')
    return render(request, 'booking/venue_confirm_delete.html', {'venue': venue})


# ─────────────────────────────────────────────────────────────────────────────
#  Bo'sh vaqt-slotlar (AJAX) — sana/usta/xizmatga qarab
# ─────────────────────────────────────────────────────────────────────────────
def venue_slots(request, pk):
    venue = get_object_or_404(Venue, pk=pk, is_active=True)
    date_str = request.GET.get('date', '')
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'slots': [], 'error': 'bad_date'})

    staff = venue.staff.filter(pk=request.GET.get('staff')).first() \
        if request.GET.get('staff') else None
    service = venue.services.filter(pk=request.GET.get('service')).first() \
        if request.GET.get('service') else None
    dur = service.duration_minutes if service else 30

    return JsonResponse({'slots': venue.available_slots(date, staff=staff, duration_minutes=dur)})


# ─────────────────────────────────────────────────────────────────────────────
#  Berilgan vaqtда bo'sh ustalar (rasm/baho/statistika bilan) — AJAX
# ─────────────────────────────────────────────────────────────────────────────
def venue_staff_at(request, pk):
    venue = get_object_or_404(Venue, pk=pk, is_active=True)
    try:
        date = datetime.strptime(request.GET.get('date', ''), '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'staff': []})
    start = _parse_time(request.GET.get('time'))
    service = venue.services.filter(pk=request.GET.get('service')).first() \
        if request.GET.get('service') else None
    dur = service.duration_minutes if service else 30

    out = []
    for s in venue.staff.filter(is_active=True):
        out.append({
            'id': str(s.id), 'name': s.name, 'specialty': s.specialty,
            'photo': s.photo.url if s.photo else '',
            'rating': round(s.rating or 0, 1), 'reviews_count': s.reviews_count,
            'completed_count': s.completed_count, 'experience_years': s.experience_years,
            'bio': s.bio, 'available': (s.is_free_at(date, start, dur) if start else True),
        })
    # Bo'shlarini oldinga
    out.sort(key=lambda x: (not x['available'], -x['rating']))
    return JsonResponse({'staff': out})


# ─────────────────────────────────────────────────────────────────────────────
#  Bron uchun to'lov sahifasi (Payme / Click)
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='/login/')
def booking_pay(request, booking_id):
    booking = get_object_or_404(VenueBooking, pk=booking_id, user=request.user)
    if booking.status != 'pending' or not booking.total_amount:
        messages.info(request, "Bu bron to'lovni talab qilmaydi.")
        return redirect('my_venue_bookings')

    from payments.payme import payme_checkout_url
    from payments.click import click_checkout_url
    return render(request, 'booking/booking_pay.html', {
        'booking': booking,
        'payme_url': payme_checkout_url('booking', str(booking.pk), booking.total_amount),
        'click_url': click_checkout_url('booking', str(booking.pk), booking.total_amount),
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Foydalanuvchi bronni bekor qiladi (jarima ushlanadi)
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='/login/')
@require_POST
def booking_cancel(request, booking_id):
    booking = get_object_or_404(VenueBooking, pk=booking_id, user=request.user)
    if booking.status in ('cancelled', 'completed', 'no_show'):
        messages.error(request, "Bu bronni bekor qilib bo'lmaydi.")
        return redirect('my_venue_bookings')

    booking.mark_cancelled()
    if booking.penalty_amount:
        messages.warning(
            request,
            f"Bron bekor qilindi. Jarima sifatida {booking.penalty_amount} so'm ushlab "
            f"qolindi, {booking.refund_amount} so'm qaytariladi.")
    else:
        messages.success(request, "Bron bekor qilindi.")
    return redirect('my_venue_bookings')


# ─────────────────────────────────────────────────────────────────────────────
#  Egasi: xizmat va usta boshqaruvi
# ─────────────────────────────────────────────────────────────────────────────
def _own_venue(request, pk):
    venue = get_object_or_404(Venue, pk=pk)
    if venue.owner_id != request.user.id:
        return None
    return venue


@login_required(login_url='/login/')
def venue_services(request, pk):
    venue = _own_venue(request, pk)
    if venue is None:
        messages.error(request, "Ruxsat yo'q.")
        return redirect('venue_detail', pk=pk)
    return render(request, 'booking/venue_services.html', {
        'venue': venue,
        'services': venue.services.all(),
        'staff': venue.staff.all(),
    })


@login_required(login_url='/login/')
@require_POST
def service_add(request, pk):
    venue = _own_venue(request, pk)
    if venue is None:
        messages.error(request, "Ruxsat yo'q.")
        return redirect('venue_detail', pk=pk)
    name = request.POST.get('name', '').strip()
    try:
        price = int(str(request.POST.get('price', '0')).replace(' ', ''))
    except ValueError:
        price = 0
    try:
        dur = int(request.POST.get('duration_minutes', '30'))
    except ValueError:
        dur = 30
    if name and price > 0:
        VenueService.objects.create(venue=venue, name=name, price=price,
                                    duration_minutes=max(dur, 10))
        messages.success(request, "Xizmat qo'shildi. ✅")
    else:
        messages.error(request, "Nom va narx to'g'ri kiritilishi shart.")
    return redirect('venue_services', pk=pk)


@login_required(login_url='/login/')
@require_POST
def service_delete(request, service_id):
    svc = get_object_or_404(VenueService, pk=service_id)
    if svc.venue.owner_id != request.user.id:
        messages.error(request, "Ruxsat yo'q.")
        return redirect('venue_list')
    venue_pk = svc.venue_id
    svc.delete()
    messages.success(request, "Xizmat o'chirildi.")
    return redirect('venue_services', pk=venue_pk)


@login_required(login_url='/login/')
@require_POST
def staff_add(request, pk):
    venue = _own_venue(request, pk)
    if venue is None:
        messages.error(request, "Ruxsat yo'q.")
        return redirect('venue_detail', pk=pk)
    name = request.POST.get('name', '').strip()
    if name:
        st = VenueStaff(venue=venue, name=name,
                        specialty=request.POST.get('specialty', '').strip())
        photo = request.FILES.get('photo')
        if photo:
            try:
                validate_file_type(photo)
                st.photo = photo
            except Exception:
                pass
        st.save()
        messages.success(request, "Usta/ishchi qo'shildi. ✅")
    else:
        messages.error(request, "Ism kiritilishi shart.")
    return redirect('venue_services', pk=pk)


@login_required(login_url='/login/')
@require_POST
def staff_delete(request, staff_id):
    st = get_object_or_404(VenueStaff, pk=staff_id)
    if st.venue.owner_id != request.user.id:
        messages.error(request, "Ruxsat yo'q.")
        return redirect('venue_list')
    venue_pk = st.venue_id
    st.delete()
    messages.success(request, "Usta/ishchi o'chirildi.")
    return redirect('venue_services', pk=venue_pk)
