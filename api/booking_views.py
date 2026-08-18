"""Booking (joy bron qilish) API view'lari."""
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from datetime import date as _date, datetime as _datetime, timedelta

from booking.models import Venue, VenueBooking, VenueService, VenueStaff, SLOT_TYPES
from .booking_serializers import (
    VenueListSerializer, VenueDetailSerializer,
    VenueBookingSerializer, BookingCreateSerializer, VenueStaffSerializer,
    VenueOwnerSerializer, VenueWriteSerializer,
    VenueServiceWriteSerializer, VenueServiceSerializer,
    VenueStaffWriteSerializer,
)

WHOLE_DAY_TYPES = ('wedding', 'other')
# Yagona manba — booking.models.SLOT_TYPES (ilgari bu yerda nusxa ro'yxat bor
# edi va yangi tur qo'shilganda API veb bilan farq qilib qolardi).
TIME_SLOT_TYPES = SLOT_TYPES
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
        # Bron oynasi joy turiga bog'liq (klinika kengroq) — serializer'ga
        # venue'ni beramiz, aks holda u umumiy 7 kunlik oynani qo'llardi.
        ser = BookingCreateSerializer(data=request.data, context={'venue': venue})
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
        if getattr(self, 'swagger_fake_view', False):  # schema generatsiyasi (anon)
            return VenueBooking.objects.none()
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


# ── TO'YXONA EGASI — bron boshqaruvi (mobil) ────────────────────────────────
class VenueOwnerBookingsView(APIView):
    """GET — egaga tegishli joylardagi bronlar (kutilayotgan + boshqalar).

    Web `manage_bookings` bilan bir xil: {pending: [...], others: [...]}.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (VenueBooking.objects.filter(venue__owner=request.user)
              .select_related('venue', 'user', 'service', 'staff')
              .order_by('-created_at'))
        ctx = {'request': request}
        pending, others = [], []
        for b in qs:
            data = VenueBookingSerializer(b, context=ctx).data
            (pending if b.status == 'pending' else others).append(data)
        return Response({'pending': pending, 'others': others})


class VenueOwnerBookingActionView(APIView):
    """POST — egasi bron holatini o'zgartiradi: confirm / cancel / complete."""
    permission_classes = [IsAuthenticated]
    MAPPING = {'confirm': 'confirmed', 'cancel': 'cancelled', 'complete': 'completed'}

    def post(self, request, booking_id, action):
        booking = (VenueBooking.objects.select_related('venue')
                   .filter(pk=booking_id).first())
        if booking is None:
            return Response({'detail': 'Bron topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        if booking.venue.owner_id != request.user.id:
            return Response({'detail': "Bu bronni boshqarish huquqingiz yo'q."},
                            status=status.HTTP_403_FORBIDDEN)
        new_status = self.MAPPING.get(action)
        if new_status is None:
            return Response({'detail': "Noma'lum amal."}, status=status.HTTP_400_BAD_REQUEST)
        if booking.status in ('cancelled', 'completed', 'no_show'):
            return Response({'detail': "Bu bron holatini o'zgartirib bo'lmaydi."},
                            status=status.HTTP_400_BAD_REQUEST)
        booking.status = new_status
        booking.save(update_fields=['status'])
        return Response(VenueBookingSerializer(booking, context={'request': request}).data)


def _own_venue(request, venue_id):
    """Egaga tegishli joyni qaytaradi (is_active'дан qat'i nazar) yoki None."""
    return Venue.objects.filter(pk=venue_id, owner=request.user).first()


class MyVenuesView(APIView):
    """GET — egaga tegishli joylar ro'yxati. POST — yangi joy yaratish."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Venue.objects.filter(owner=request.user).order_by('-created_at')
        return Response(VenueListSerializer(qs, many=True, context={'request': request}).data)

    def post(self, request):
        ser = VenueWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            venue = ser.save(owner=request.user, is_active=True)
            # Joy ochgan foydalanuvchi avtomatik 'business' roliga o'tadi (web bilan bir xil)
            if request.user.role == 'user':
                request.user.role = 'business'
                request.user.save(update_fields=['role'])
        return Response(VenueOwnerSerializer(venue, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


class MyVenueDetailView(APIView):
    """GET — egasi uchun to'liq joy (tahrir + xizmat/usta). PATCH — tahrir. DELETE — o'chirish."""
    permission_classes = [IsAuthenticated]

    def get(self, request, venue_id):
        venue = _own_venue(request, venue_id)
        if venue is None:
            return Response({'detail': 'Joy topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(VenueOwnerSerializer(venue, context={'request': request}).data)

    def patch(self, request, venue_id):
        venue = _own_venue(request, venue_id)
        if venue is None:
            return Response({'detail': 'Joy topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        ser = VenueWriteSerializer(venue, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(VenueOwnerSerializer(venue, context={'request': request}).data)

    def delete(self, request, venue_id):
        venue = _own_venue(request, venue_id)
        if venue is None:
            return Response({'detail': 'Joy topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        venue.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyVenueServiceView(APIView):
    """POST — joyга xizmat qo'shadi."""
    permission_classes = [IsAuthenticated]

    def post(self, request, venue_id):
        venue = _own_venue(request, venue_id)
        if venue is None:
            return Response({'detail': 'Joy topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        ser = VenueServiceWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        svc = ser.save(venue=venue, is_active=True)
        return Response(VenueServiceSerializer(svc, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


class MyVenueServiceDeleteView(APIView):
    """DELETE — o'z joyining xizmatini o'chiradi."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, service_id):
        svc = VenueService.objects.filter(
            pk=service_id, venue__owner=request.user).first()
        if svc is None:
            return Response({'detail': 'Xizmat topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        svc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyVenueStaffView(APIView):
    """POST — joyга usta/ishchi qo'shadi (rasm bilan — multipart)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, venue_id):
        venue = _own_venue(request, venue_id)
        if venue is None:
            return Response({'detail': 'Joy topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        ser = VenueStaffWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        st = ser.save(venue=venue, is_active=True)
        return Response(VenueStaffSerializer(st, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


class MyVenueStaffDeleteView(APIView):
    """DELETE — o'z joyining ustasini o'chiradi."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, staff_id):
        st = VenueStaff.objects.filter(
            pk=staff_id, venue__owner=request.user).first()
        if st is None:
            return Response({'detail': 'Usta topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        st.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
