from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone

from .models import Provider, ServicePayment, CATEGORY_CHOICES


def payments_home(request):
    cat = request.GET.get('cat', '').strip()
    q = request.GET.get('q', '').strip()

    providers = Provider.objects.filter(is_active=True)
    if cat:
        providers = providers.filter(category=cat)
    if q:
        providers = providers.filter(Q(name__icontains=q) | Q(description__icontains=q))

    return render(request, 'payments/home.html', {
        'providers': providers,
        'categories': CATEGORY_CHOICES,
        'cat': cat,
        'q': q,
    })


@login_required
def pay(request, provider_pk):
    provider = get_object_or_404(Provider, pk=provider_pk, is_active=True)

    if request.method == 'POST':
        payer_name = request.POST.get('payer_name', '').strip()
        period = request.POST.get('period', '').strip()

        # Summa: belgilangan bo'lsa o'sha, aks holda foydalanuvchi kiritadi
        if provider.has_fixed_amount:
            amount = provider.amount
        else:
            try:
                amount = int(''.join(c for c in request.POST.get('amount', '') if c.isdigit()))
            except ValueError:
                amount = 0
            if amount <= 0:
                messages.error(request, "Summani to'g'ri kiriting.")
                return render(request, 'payments/pay.html', {'provider': provider})

        # Karta (simulyatsiya)
        card_number = request.POST.get('card_number', '')
        card_holder = request.POST.get('card_holder', '').strip()
        expiry = request.POST.get('expiry', '').strip()
        cvv = request.POST.get('cvv', '').strip()
        digits = ''.join(c for c in card_number if c.isdigit())

        if len(digits) < 16 or len(cvv) < 3 or not expiry:
            messages.error(request, "Karta ma'lumotlari to'liq emas.")
            return render(request, 'payments/pay.html', {'provider': provider})

        # DIQQAT: to'liq karta raqami va CVV SAQLANMAYDI — faqat oxirgi 4 raqam.
        payment = ServicePayment.objects.create(
            user=request.user, provider=provider,
            provider_name=provider.name, category=provider.category,
            payer_name=payer_name, period=period, amount=amount,
            card_holder=card_holder, card_last4=digits[-4:],
            card_brand=ServicePayment.detect_brand(digits),
            status='paid', paid_at=timezone.now(),
        )
        messages.success(request, "To'lov muvaffaqiyatli amalga oshirildi! ✅")
        return redirect('payments:receipt', payment_id=payment.id)

    return render(request, 'payments/pay.html', {'provider': provider})


@login_required
def receipt(request, payment_id):
    payment = get_object_or_404(ServicePayment, pk=payment_id, user=request.user)
    return render(request, 'payments/receipt.html', {'payment': payment})


@login_required
def my_payments(request):
    payments = ServicePayment.objects.filter(user=request.user)
    return render(request, 'payments/my_payments.html', {'payments': payments})
