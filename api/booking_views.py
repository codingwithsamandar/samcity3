"""Booking (joy bron qilish) API view'lari."""
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from datetime import date as _date, datetime as _datetime, timedelta

from booking.models import Venue, VenueBooking
from .booking_serializers import (
    VenueListSerializer, VenueDetailSerializer,
    VenueBookingSerializer, BookingCreateSerializer,
)

WHOLE_DAY_TYPES = ('wedding', 'other')
TIME_SLOT_TYPES = ('barber', 'beauty', 'restaurant', 'cafe')
ACTIVE_STATUSES = ('pending', 'confirmed')


def _conflict(venue, booking_date, start, end, staff=None):
    qs = VenueBooking.objects.filter(
        venue=venue, booking_date=booking_date, status__in=ACTIVE_STATUSES)
    if staff is not None:
        qs = qs.filter(staff=staff)
    vt = venue.venue_type
    if vt in WHOLE_DAY_TYPES:
        return qs.exists()
    if vt in TIME_SLOT_TYPES and start:
        for b in qs:
            if not b.start_time:
                continue
            b_end = b.end_time or b.start_time
            new_end = end or start
            if start < b_end and b.start_time < new_end:
                return True
            if start == b.start_time:
                return True
    return False


def _estimate_total(venue, start, end, service=None):
    if service is not None:
        return int(service.price)
    vt = venue.venue_type
    if vt == 'gym':
        return venue.price_per_day or venue.price_per_hour or 0
    if vt in TIME_SLOT_TYPES:
        if venue.price_per_hour and start and end:
            hours = max(1, end.hour - start.hour)
            return venue.price_per_hour * hours
        return venue.price_per_hour or venue.price_per_day or 0
    return venue.price_per_day or venue.price_per_hour or 0


class VenueViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['venue_type']
    search_fields = ['name', 'address', 'description']

    def get_queryset(self):
        return Venue.objects.filter(is_active=True)

    def get_serializer_class(self):
        return VenueDetailSerializer if self.action == 'retrieve' else VenueListSerializer

    @action(detail=True, methods=['get'])
    def slots(self, request, pk=None):
        """Bo'sh vaqt-slotlar: ?date=YYYY-MM-DD&staff=<id>&service=<id>."""
        venue = self.get_object()
        try:
            date = _datetime.strptime(request.query_params.get('date', ''), '%Y-%m-%d').date()
        except ValueError:
            return Response({'slots': []})
        staff = venue.staff.filter(pk=request.query_params.get('staff')).first() \
            if request.query_params.get('staff') else None
        service = venue.services.filter(pk=request.query_params.get('service')).first() \
            if request.query_params.get('service') else None
        dur = service.duration_minutes if service else 30
        return Response({'slots': venue.available_slots(date, staff=staff, duration_minutes=dur)})

    @action(detail=True, methods=['get'], url_path='staff-at')
    def staff_at(self, request, pk=None):
        """Berilgan vaqtда bo'sh ustalar (rasm/baho/statistika bilan).

        ?date=YYYY-MM-DD&time=HH:MM&service=<id>
        """
        venue = self.get_object()
        try:
            date = _datetime.strptime(request.query_params.get('date', ''), '%Y-%m-%d').date()
        except ValueError:
            return Response({'staff': []})
        tstr = request.query_params.get('time', '')
        start = None
        for fmt in ('%H:%M', '%H:%M:%S'):
            try:
                start = _datetime.strptime(tstr, fmt).time()
                break
            except ValueError:
                continue
        service = venue.services.filter(pk=request.query_params.get('service')).first() \
            if request.query_params.get('service') else None
        dur = service.duration_minutes if service else 30

        out = []
        for s in venue.staff.filter(is_active=True):
            data = VenueStaffSerializer(s, context={'request': request}).data
            data['available'] = s.is_free_at(date, start, dur) if start else True
            out.append(data)
        out.sort(key=lambda x: (not x['available'], -(x.get('rating') or 0)))
        return Response({'staff': out})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def book(self, request, pk=None):
        venue = self.get_object()
        ser = BookingCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        start, end = d.get('start_time'), d.get('end_time')
        service = venue.services.filter(pk=d.get('service'), is_active=True).first() \
            if d.get('service') else None
        staff = venue.staff.filter(pk=d.get('staff'), is_active=True).first() \
            if d.get('staff') else None

        if venue.uses_slots:
            if service is None:
                return Response({'detail': "Xizmatni tanlang."},
                                status=status.HTTP_400_BAD_REQUEST)
            if start is None:
                return Response({'detail': "Vaqtni tanlang."},
                                status=status.HTTP_400_BAD_REQUEST)
            end = (_datetime.combine(_date.today(), start)
                   + timedelta(minutes=service.duration_minutes)).time()

        # Venue qatorini lock qilamiz — double-booking himoyasi.
        with transaction.atomic():
            Venue.objects.select_for_update().filter(pk=venue.pk).first()
            if _conflict(venue, d['booking_date'], start, end,
                         staff=staff if venue.uses_slots else None):
                return Response(
                    {'detail': "Bu vaqt allaqachon band. Boshqa vaqt/usta tanlang."},
                    status=status.HTTP_409_CONFLICT)

            booking = VenueBooking(
                venue=venue, user=request.user, status='pending',
                booking_date=d['booking_date'], start_time=start, end_time=end,
                service=service, staff=staff,
                guests=d.get('guests', 1) or 1, message=d.get('message', ''),
            )
            vt = venue.venue_type
            if vt == 'wedding':
                booking.event_type = d.get('event_type', '')
                booking.decoration_needed = d.get('decoration_needed', False)
            elif vt in ('restaurant', 'cafe'):
                booking.table_count = d.get('table_count', 1) or 1
                booking.special_request = d.get('special_request', '')
            elif vt == 'gym':
                booking.subscription_type = d.get('subscription_type', '')
            if service:
                booking.service_type = service.name
            if staff:
                booking.master_name = staff.name

            booking.total_amount = _estimate_total(venue, start, end, service=service)
            booking.save()

        # Joy egasiga bildirishnoma (o'zining joyiga bron qilmasa).
        try:
            owner = getattr(venue, 'owner', None)
            if owner is not None and owner.id != request.user.id:
                from notifications.models import notify
                from django.urls import reverse
                try:
                    _url = reverse('manage_bookings')
                except Exception:
                    _url = ''
                notify(owner, f"Yangi bron: {venue.name} ({booking.booking_date}) 📅",
                       _url, 'booking')
        except Exception:
            pass

        return Response(
            VenueBookingSerializer(booking, context={'request': request}).data,
            status=status.HTTP_201_CREATED)


class VenueBookingViewSet(viewsets.ReadOnlyModelViewSet):
    """Foydalanuvchining bronlari + bekor qilish."""
    permission_classes = [IsAuthenticated]
    serializer_class = VenueBookingSerializer

    def get_queryset(self):
        return (VenueBooking.objects.filter(user=self.request.user)
                .select_related('venue').order_by('-created_at'))

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.status in ('cancelled', 'completed', 'no_show'):
            return Response({'detail': "Bu bronni bekor qilib bo'lmaydi."},
                            status=status.HTTP_400_BAD_REQUEST)
        # Jarima ushlanadi (to'langan bo'lsa), qolgani qaytariladi.
        booking.mark_cancelled()
        return Response(VenueBookingSerializer(booking, context={'request': request}).data)
