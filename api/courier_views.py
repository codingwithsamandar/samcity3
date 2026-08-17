"""Kuryer (yetkazib beruvchi) mobil API — web driver_* view'lariga mos.

Endpointlar (hammasi autentifikatsiya talab qiladi):
    GET   /api/courier/                     — dashboard (profil + buyurtmalar + daromad)
    POST  /api/courier/register/            — kuryer profili yaratish
    PATCH /api/courier/profile/             — profilni yangilash
    POST  /api/courier/available/           — bo'sh/band holatini almashtirish
    POST  /api/courier/orders/<id>/accept/  — tayyor buyurtmani qabul qilish
    POST  /api/courier/orders/<id>/release/ — biriktirilgan buyurtmadan voz kechish
    POST  /api/courier/orders/<id>/status/  — holat: picked_up / on_the_way / delivered

Web bilan bir xil qoidalar: qabulda select_for_update (ikki kuryer bir
buyurtmani ololmaydi), can_transition holat tekshiruvi, real-time push.
"""
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from delivery.models import DeliveryDriver, Order, can_transition
from .delivery_serializers import (
    DeliveryDriverSerializer, DeliveryDriverWriteSerializer, OrderSerializer,
)
from .delivery_views import _push_order_status_safe


def _get_driver(user):
    return DeliveryDriver.objects.filter(user=user).first()


def _get_working_driver(user):
    """Buyurtma olishga haqli kuryer — `is_active=False` bo'lsa admin bloklagan.

    Web `delivery.views._get_working_driver` bilan bir xil qoida. Bloklangan
    kuryer buyurtma qabul qila olmasligi VA mijozlarning manzil/telefonini
    ko'rmasligi kerak. Avval mobil API buni tekshirmasdi — bloklangan kuryer
    ilova orqali ishlashda davom etardi.
    """
    return DeliveryDriver.objects.filter(user=user, is_active=True).first()


def _orders_ctx(request):
    return {'request': request}


class CourierDashboardView(APIView):
    """GET — kuryer profili, buyurtmalar (qabul mumkin / faol / tarix) va daromad.

    Profil bo'lmasa {registered: false} qaytaradi (mobil ro'yxatdan o'tishga yo'naltiradi).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        driver = _get_driver(request.user)
        if not driver:
            return Response({'registered': False})

        base = Order.objects.select_related('driver').prefetch_related('items')
        available = base.filter(status='ready', driver__isnull=True,
                                fulfillment_type='delivery').order_by('-created_at')
        # Bloklangan kuryer mijozlarning manzil/telefonini ko'rmasligi kerak
        # (web `_driver_queues` bilan bir xil). Faol buyurtmalar/tarix ochiq —
        # allaqachon qo'lidagi yetkazishni yakunlashi mumkin.
        if not driver.is_active:
            available = available.none()
        active = base.filter(driver=driver,
                             status__in=['assigned', 'picked_up', 'on_the_way']).order_by('-assigned_at')
        history = base.filter(driver=driver, status='delivered').order_by('-delivered_at')

        now = timezone.localtime()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        dated = history.filter(delivered_at__isnull=False)
        ctx = _orders_ctx(request)

        def _sum(qs):
            return int(qs.aggregate(s=Sum('delivery_fee'))['s'] or 0)

        return Response({
            'registered': True,
            'driver': DeliveryDriverSerializer(driver, context=ctx).data,
            'available': OrderSerializer(available, many=True, context=ctx).data,
            'active': OrderSerializer(active, many=True, context=ctx).data,
            'history': OrderSerializer(history[:20], many=True, context=ctx).data,
            'stats': {
                'delivered_count': history.count(),
                'active_count': active.count(),
                'earnings_total': _sum(history),
                'earnings_today': _sum(dated.filter(delivered_at__gte=today_start)),
                'earnings_week': _sum(dated.filter(delivered_at__gte=now - timedelta(days=7))),
                'earnings_month': _sum(dated.filter(delivered_at__gte=now - timedelta(days=30))),
            },
        })


class CourierRegisterView(APIView):
    """POST — kuryer profili yaratadi (bir foydalanuvchi = bitta profil)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if _get_driver(request.user):
            return Response({'detail': 'Kuryer profili allaqachon mavjud.'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = DeliveryDriverWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            driver = ser.save(user=request.user)
            if request.user.role == 'user':
                request.user.role = 'driver'
                request.user.save(update_fields=['role'])
        return Response(DeliveryDriverSerializer(driver, context=_orders_ctx(request)).data,
                        status=status.HTTP_201_CREATED)


class CourierProfileView(APIView):
    """PATCH — profilni yangilaydi."""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        driver = _get_driver(request.user)
        if not driver:
            return Response({'detail': 'Kuryer profili topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        ser = DeliveryDriverWriteSerializer(driver, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(DeliveryDriverSerializer(driver, context=_orders_ctx(request)).data)


class CourierAvailableView(APIView):
    """POST — bo'sh/band holatini almashtiradi. {is_available} bilan ham o'rnatish mumkin."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        driver = _get_working_driver(request.user)
        if not driver:
            if _get_driver(request.user):
                return Response({'detail': 'Hisobingiz bloklangan.'},
                                status=status.HTTP_403_FORBIDDEN)
            return Response({'detail': 'Kuryer profili topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        val = request.data.get('is_available')
        driver.is_available = (not driver.is_available) if val is None else bool(val)
        driver.save(update_fields=['is_available'])
        return Response({'is_available': driver.is_available})


class CourierAcceptView(APIView):
    """POST — tayyor buyurtmani qabul qiladi (race himoyasi bilan)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        # Yangi buyurtma olish — bloklangan kuryerga ruxsat yo'q (web bilan bir xil).
        driver = _get_working_driver(request.user)
        if not driver:
            if _get_driver(request.user):
                return Response({'detail': 'Hisobingiz bloklangan — buyurtma qabul qila olmaysiz.'},
                                status=status.HTTP_403_FORBIDDEN)
            return Response({'detail': 'Kuryer profili topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        if not driver.is_available:
            return Response({'detail': "Avval «Bo'sh» holatiga o'ting."},
                            status=status.HTTP_400_BAD_REQUEST)
        order = None
        with transaction.atomic():
            locked = (Order.objects.select_for_update()
                      .filter(pk=order_id, status='ready', driver__isnull=True,
                              fulfillment_type='delivery').first())
            if locked is not None:
                locked.driver = driver
                locked.status = 'assigned'
                locked.assigned_at = timezone.now()
                locked.save(update_fields=['driver', 'status', 'assigned_at'])
                order = locked
        if order is None:
            return Response({'detail': 'Buyurtma allaqachon olingan yoki mavjud emas.'},
                            status=status.HTTP_409_CONFLICT)
        _push_order_status_safe(order)
        return Response(OrderSerializer(order, context=_orders_ctx(request)).data)


class CourierReleaseView(APIView):
    """POST — biriktirilgan buyurtmadan voz kechadi (yana 'ready' bo'ladi)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        driver = _get_driver(request.user)
        if not driver:
            return Response({'detail': 'Kuryer profili topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        order = Order.objects.filter(pk=order_id, driver=driver, status='assigned').first()
        if order is None:
            return Response({'detail': 'Voz kechish mumkin bo\'lgan buyurtma topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        order.driver = None
        order.status = 'ready'
        order.assigned_at = None
        order.save(update_fields=['driver', 'status', 'assigned_at'])
        _push_order_status_safe(order)
        return Response(OrderSerializer(order, context=_orders_ctx(request)).data)


class CourierOrderStatusView(APIView):
    """POST {status} — kuryer buyurtma holatini o'zgartiradi (picked_up/on_the_way/delivered)."""
    permission_classes = [IsAuthenticated]
    ALLOWED = {'picked_up', 'on_the_way', 'delivered'}

    def post(self, request, order_id):
        driver = _get_driver(request.user)
        if not driver:
            return Response({'detail': 'Kuryer profili topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        order = Order.objects.filter(pk=order_id, driver=driver).first()
        if order is None:
            return Response({'detail': 'Buyurtma topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get('status', '')
        if new_status not in self.ALLOWED:
            return Response({'detail': "Bu holatni kuryer o'zgartira olmaydi."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not can_transition(order.status, new_status, order.fulfillment_type):
            return Response({'detail': "Bu holatga o'tib bo'lmaydi."},
                            status=status.HTTP_409_CONFLICT)
        order.status = new_status
        update_fields = ['status']
        if new_status == 'delivered':
            order.delivered_at = timezone.now()
            update_fields.append('delivered_at')
        order.save(update_fields=update_fields)
        _push_order_status_safe(order)
        return Response(OrderSerializer(order, context=_orders_ctx(request)).data)
