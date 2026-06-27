"""Taksi API view'lari: xizmatlar, taksistlar, sayohatlar."""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from taxi.models import TaxiService, Taxist, Route, Trip
from .taxi_serializers import (
    TaxiServiceSerializer, TaxistListSerializer, TaxistDetailSerializer,
    TripSerializer, TripCreateSerializer,
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
