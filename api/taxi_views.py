"""Taksi API view'lari: xizmatlar, taksistlar, sayohatlar, haydovchi paneli."""
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from taxi.models import TaxiService, Taxist, Route, Trip
from .taxi_serializers import (
    TaxiServiceSerializer, TaxistListSerializer, TaxistDetailSerializer,
    TripSerializer, TripCreateSerializer, RouteSerializer,
    TaxistSelfSerializer, TaxistWriteSerializer, RouteWriteSerializer,
    DriverTripSerializer,
)


class TaxiServiceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = TaxiServiceSerializer
    search_fields = ['name', 'short_number', 'region']

    def get_queryset(self):
        return TaxiService.objects.filter(is_active=True)


class TaxistViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ['full_name', 'car_model', 'region']

    def get_queryset(self):
        return (Taxist.objects.filter(is_active=True)
                .select_related('car').prefetch_related('routes', 'reviews'))

    def get_serializer_class(self):
        return TaxistDetailSerializer if self.action == 'retrieve' else TaxistListSerializer


class TripViewSet(viewsets.ReadOnlyModelViewSet):
    """Mening sayohatlarim + sayohat yaratish (buyurtma)."""
    permission_classes = [IsAuthenticated]
    serializer_class = TripSerializer

    def get_queryset(self):
        return (Trip.objects.filter(passenger=self.request.user)
                .select_related('taxist').order_by('-created_at'))

    def create(self, request, *args, **kwargs):
        ser = TripCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        route_id = ser.validated_data['route_id']
        is_delivery = ser.validated_data['is_delivery']

        route = Route.objects.select_related('taxist').filter(
            pk=route_id, taxist__is_active=True).first()
        if route is None:
            return Response({'detail': 'Marshrut topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)

        if is_delivery and route.delivery_price:
            price = route.delivery_price
        else:
            is_delivery = False
            price = route.passenger_price

        trip = Trip.objects.create(
            passenger=request.user, taxist=route.taxist, route=route,
            point_a=route.point_a, point_b=route.point_b,
            is_delivery=is_delivery, price=price,
            status='accepted', payment_method='card', payment_status='unpaid',
        )

        # Taksistга bildirishnoma (uning hisobi bo'lsa). notify() None'ni xavfsiz
        # qabul qiladi, shuning uchun user bog'lanmagan bo'lsa o'tkazib yuboriladi.
        try:
            from notifications.models import notify
            from django.urls import reverse
            label = 'Yangi yetkazma' if is_delivery else 'Yangi sayohat buyurtmasi'
            notify(
                getattr(route.taxist, 'user', None),
                f"{label}: {route.point_a} → {route.point_b} 🚕",
                reverse('taxi:taxist_manage'), 'taxi',
            )
        except Exception:
            pass

        return Response(TripSerializer(trip, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
#  HAYDOVCHI (TAKSIST) MOBIL PANELI — web taxist_manage/route_* view'lariga mos
# ─────────────────────────────────────────────────────────────────────────────
def _get_taxist(user):
    return Taxist.objects.filter(user=user).select_related('car').first()


def _ensure_taxi_service():
    """Kamida bitta faol TaxiService bo'lishini ta'minlaydi (web bilan bir xil)."""
    svc = TaxiService.objects.filter(is_active=True).first()
    if svc:
        return svc
    return TaxiService.objects.create(
        name='SamCity Taksi', short_number='1265', is_active=True,
        working_hours='24/7', base_price=5000, price_per_km=2000,
    )


class TaxistMeView(APIView):
    """GET — haydovchi profili + marshrutlar + sayohatlar + statistika.

    Profil bo'lmasa {registered: false} qaytaradi (mobil ro'yxatdan o'tishga yo'naltiradi).
    PATCH — profil (ism, telefon, mashina, hudud) tahriri.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        taxist = _get_taxist(request.user)
        if not taxist:
            return Response({'registered': False})
        ctx = {'request': request}
        trips = (Trip.objects.filter(taxist=taxist)
                 .select_related('passenger').order_by('-created_at'))
        active = trips.filter(status__in=['searching', 'accepted', 'on_way'])
        history = trips.filter(status__in=['completed', 'cancelled'])
        completed = history.filter(status='completed')
        routes = taxist.routes.all()
        return Response({
            'registered': True,
            'taxist': TaxistSelfSerializer(taxist, context=ctx).data,
            'routes': RouteSerializer(routes, many=True, context=ctx).data,
            'active': DriverTripSerializer(active, many=True, context=ctx).data,
            'history': DriverTripSerializer(history[:20], many=True, context=ctx).data,
            'stats': {
                'trips_count': taxist.trips_count,
                'routes_count': routes.count(),
                'active_count': active.count(),
                'completed_count': completed.count(),
                'earnings_total': int(completed.aggregate(s=Sum('price'))['s'] or 0),
            },
        })

    def patch(self, request):
        taxist = _get_taxist(request.user)
        if not taxist:
            return Response({'detail': 'Taksist profili topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        ser = TaxistWriteSerializer(taxist, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(TaxistSelfSerializer(taxist, context={'request': request}).data)


class TaxistRegisterView(APIView):
    """POST — taksist profili yaratadi (bir foydalanuvchi = bitta profil)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if _get_taxist(request.user):
            return Response({'detail': 'Taksist profili allaqachon mavjud.'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = TaxistWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            taxist = ser.save(user=request.user, is_active=True,
                              service=_ensure_taxi_service())
            if request.user.role == 'user':
                request.user.role = 'driver'
                request.user.save(update_fields=['role'])
        return Response(TaxistSelfSerializer(taxist, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


class TaxistOnlineToggleView(APIView):
    """POST — onlayn/oflayn holatini almashtiradi. {is_online} bilan aniq o'rnatish mumkin."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        taxist = _get_taxist(request.user)
        if not taxist:
            return Response({'detail': 'Taksist profili topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        val = request.data.get('is_online')
        taxist.is_online = (not taxist.is_online) if val is None else bool(val)
        taxist.location_updated_at = timezone.now()
        taxist.save(update_fields=['is_online', 'location_updated_at'])
        return Response({'is_online': taxist.is_online})


class TaxistRouteCreateView(APIView):
    """POST — AB marshrut qo'shadi."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        taxist = _get_taxist(request.user)
        if not taxist:
            return Response({'detail': 'Taksist profili topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        ser = RouteWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        route = ser.save(taxist=taxist, is_active=True)
        return Response(RouteSerializer(route, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


class TaxistRouteDeleteView(APIView):
    """DELETE — o'z marshrutini o'chiradi."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, route_id):
        taxist = _get_taxist(request.user)
        if not taxist:
            return Response({'detail': 'Taksist profili topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        route = Route.objects.filter(pk=route_id, taxist=taxist).first()
        if route is None:
            return Response({'detail': 'Marshrut topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        route.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
