"""To'lov (Payme / Click) — mobil ilova uchun API.

`POST /api/payments/initiate/` — berilgan obyekt (buyurtma/sayohat/bron/xizmat)
uchun to'lov URL'larini qaytaradi. Foydalanuvchi faqat o'ziga tegishli obyekt
uchun to'lov boshlay oladi.
"""
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.gateways import resolve_target, PAYABLES
from payments.payme import payme_checkout_url
from payments.click import click_checkout_url
from .throttles import PaymentInitThrottle


class InitiatePaymentSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=list(PAYABLES.keys()))
    target_id = serializers.CharField(max_length=64)


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [PaymentInitThrottle]

    def post(self, request):
        ser = InitiatePaymentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ttype = ser.validated_data['target_type']
        tid = ser.validated_data['target_id']

        obj, ops = resolve_target(ttype, tid)
        if obj is None:
            return Response({'detail': 'Obyekt topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        if ops['owner'](obj) != request.user.id:
            return Response({'detail': "Bu to'lovga ruxsatingiz yo'q."},
                            status=status.HTTP_403_FORBIDDEN)
        if ops['is_paid'](obj):
            return Response({'detail': "Allaqachon to'langan.", 'paid': True},
                            status=status.HTTP_409_CONFLICT)

        amount = ops['amount'](obj)
        if amount <= 0:
            return Response({'detail': "To'lov summasi noto'g'ri."},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'target_type': ttype,
            'target_id': tid,
            'amount': amount,
            'payme_url': payme_checkout_url(ttype, tid, amount),
            'click_url': click_checkout_url(ttype, tid, amount),
        })
