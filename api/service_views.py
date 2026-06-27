"""Xizmat / kommunal to'lovlari — mobil API.

Provayderlar (muassasalar) ro'yxati + to'lov yozuvi yaratish. Yaratilgach,
ilova `/api/payments/initiate/` (target_type='service') orqali Payme/Click bilan
to'laydi.
"""
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import Provider, ServicePayment, CATEGORY_CHOICES


def _abs(request, field):
    if not field:
        return None
    return request.build_absolute_uri(field.url) if request else field.url


class ProviderSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    logo = serializers.SerializerMethodField()
    has_fixed_amount = serializers.BooleanField(read_only=True)

    class Meta:
        model = Provider
        fields = ('id', 'name', 'category', 'category_label', 'description',
                  'address', 'phone', 'logo', 'amount', 'has_fixed_amount', 'region')

    def get_logo(self, obj):
        return _abs(self.context.get('request'), obj.logo)


class ServicePaymentSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ServicePayment
        fields = ('id', 'provider_name', 'category', 'category_label', 'payer_name',
                  'period', 'amount', 'status', 'status_label', 'created_at', 'paid_at')


class ProvidersListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        qs = Provider.objects.filter(is_active=True)
        cat = request.query_params.get('category')
        if cat:
            qs = qs.filter(category=cat)
        ser = ProviderSerializer(qs, many=True, context={'request': request})
        return Response({
            'categories': [{'key': k, 'label': v} for k, v in CATEGORY_CHOICES],
            'results': ser.data,
        })


class CreateServicePaymentView(APIView):
    """To'lov yozuvini yaratadi (pending). Keyin /payments/initiate/ bilan to'lanadi."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        provider = Provider.objects.filter(
            pk=request.data.get('provider'), is_active=True).first()
        if provider is None:
            return Response({'detail': 'Muassasa topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        try:
            amount = int(str(request.data.get('amount') or provider.amount or 0).replace(' ', ''))
        except (ValueError, TypeError):
            amount = 0
        if amount <= 0:
            return Response({'detail': "Summa noto'g'ri."},
                            status=status.HTTP_400_BAD_REQUEST)

        payment = ServicePayment.objects.create(
            user=request.user, provider=provider, provider_name=provider.name,
            category=provider.category, amount=amount, status='pending',
            payer_name=(request.data.get('payer_name') or '').strip(),
            period=(request.data.get('period') or '').strip(),
        )
        return Response(ServicePaymentSerializer(payment).data,
                        status=status.HTTP_201_CREATED)


class MyServicePaymentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = ServicePayment.objects.filter(user=request.user)
        return Response({'results': ServicePaymentSerializer(qs, many=True).data})
