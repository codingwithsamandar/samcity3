"""Marketplace (ad favorites/reports/inquiries) + global search views."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, F

from .models import Ad, AdFavorite, AdReport, AdInquiry, SearchQuery, JobAd


# ── Ad favorites ─────────────────────────────────────────────────────────────
@login_required
@require_POST
def ad_favorite_toggle(request, pk):
    ad = get_object_or_404(Ad, pk=pk)
    fav = AdFavorite.objects.filter(ad=ad, user=request.user).first()
    if fav:
        fav.delete()
        active = False
    else:
        AdFavorite.objects.create(ad=ad, user=request.user)
        active = True
    # Yurakcha (saqlash) — savatning e'lonlar bo'limi bilan sinxron: saqlansa
    # savatga qo'shiladi, olib tashlansa savatdan ham chiqadi.
    try:
        from delivery.models import CartAd, get_active_cart
        cart = get_active_cart(request.user)
        if active:
            CartAd.objects.get_or_create(cart=cart, ad=ad)
        else:
            CartAd.objects.filter(cart=cart, ad=ad).delete()
    except Exception:
        pass
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'favorite': active})
    return redirect('ad_detail', pk=pk)


@login_required
def saved_ads(request):
    favs = (AdFavorite.objects.filter(user=request.user)
            .select_related('ad__user').prefetch_related('ad__images'))
    return render(request, 'saved_ads.html', {'favorites': favs})


# ── Ad report ────────────────────────────────────────────────────────────────
@login_required
@require_POST
def ad_report(request, pk):
    ad = get_object_or_404(Ad, pk=pk)
    AdReport.objects.create(
        ad=ad, reporter=request.user,
        reason=request.POST.get('reason', 'other'),
        detail=request.POST.get('detail', '').strip()[:500],
    )
    # Notify staff
    try:
        from notifications.models import notify
        from django.contrib.auth import get_user_model
        from django.urls import reverse
        for staff in get_user_model().objects.filter(is_staff=True):
            notify(staff, f"E'lon shikoyati: {ad.title[:40]}", reverse('ad_detail', args=[ad.pk]), 'system')
    except Exception:
        pass
    messages.success(request, "Shikoyatingiz qabul qilindi. Tekshiramiz.")
    return redirect('ad_detail', pk=pk)


# ── Buyer ↔ seller inquiry ───────────────────────────────────────────────────
@login_required
@require_POST
def ad_inquiry(request, pk):
    ad = get_object_or_404(Ad.objects.select_related('user'), pk=pk)
    msg = request.POST.get('message', '').strip()
    if not msg:
        messages.error(request, "Xabar bo'sh bo'lmasligi kerak.")
        return redirect('ad_detail', pk=pk)
    AdInquiry.objects.create(ad=ad, sender=request.user, message=msg[:2000])
    if ad.user_id != request.user.id:
        try:
            from notifications.models import notify
            from django.urls import reverse
            notify(ad.user, f"E'loningizga savol: {ad.title[:40]}", reverse('ad_detail', args=[ad.pk]), 'ads')
        except Exception:
            pass
    messages.success(request, "Xabaringiz sotuvchiga yuborildi. ✅")
    return redirect('ad_detail', pk=pk)


@login_required
def my_inquiries(request):
    """Markaziy "Kelgan savollar" — foydalanuvchining BARCHA e'lonlariga kelgan
    savollar bir joyda (avval har e'lonni alohida ochish kerak edi).

    Ochilganda o'qilmaganlar o'qilgan deb belgilanadi (badge nolga tushadi).
    """
    qs = (AdInquiry.objects
          .filter(ad__user=request.user)
          .select_related('ad', 'sender')
          .order_by('-created_at'))
    unread_ids = list(qs.filter(is_read=False).values_list('id', flat=True))
    inquiries = list(qs[:200])
    if unread_ids:
        AdInquiry.objects.filter(id__in=unread_ids).update(is_read=True)
    return render(request, 'my_inquiries.html', {
        'inquiries': inquiries,
        'unread_ids': set(unread_ids),  # shu ochilishda yangi bo'lganlarni ajratish
    })


def unread_inquiry_count(user):
    """Foydalanuvchi e'lonlariga kelgan o'qilmagan savollar soni (badge uchun)."""
    if not user.is_authenticated:
        return 0
    return AdInquiry.objects.filter(ad__user=user, is_read=False).count()


# ── Global search ────────────────────────────────────────────────────────────
def _record_term(term):
    term = (term or '').strip().lower()[:120]
    if len(term) < 2:
        return
    try:
        obj, created = SearchQuery.objects.get_or_create(term=term)
        if not created:
            SearchQuery.objects.filter(pk=obj.pk).update(count=F('count') + 1)
    except Exception:
        pass


def global_search(request):
    from places.models import Place
    q = request.GET.get('q', '').strip()
    place_results = ad_results = job_results = []
    if q:
        _record_term(q)
        # recent searches in session
        recent = request.session.get('recent_searches', [])
        recent = [q] + [r for r in recent if r != q]
        request.session['recent_searches'] = recent[:8]

        ad_results = list(
            Ad.objects.filter(status='active').filter(
                Q(title__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q)
            ).select_related('user').prefetch_related('images')[:20]
        )
        place_results = list(
            Place.objects.filter(is_active=True).filter(
                Q(name__icontains=q) | Q(address__icontains=q) | Q(description__icontains=q)
            )[:20]
        )
        job_results = list(
            JobAd.objects.filter(status='active').filter(
                Q(title__icontains=q) | Q(company__icontains=q) | Q(description__icontains=q)
            )[:20]
        )

    trending = SearchQuery.objects.all()[:8]
    return render(request, 'search_results.html', {
        'q': q,
        'ad_results': ad_results,
        'place_results': place_results,
        'job_results': job_results,
        'total': len(ad_results) + len(place_results) + len(job_results),
        'recent': request.session.get('recent_searches', []),
        'trending': trending,
    })


def search_autocomplete(request):
    """Lightweight JSON suggestions across ads + places + trending terms."""
    from places.models import Place
    q = request.GET.get('q', '').strip()
    out = []
    if len(q) >= 2:
        for a in Ad.objects.filter(status='active', title__icontains=q).values_list('title', flat=True)[:6]:
            out.append({'type': 'ad', 'text': a})
        for p in Place.objects.filter(is_active=True, name__icontains=q).values_list('name', flat=True)[:5]:
            out.append({'type': 'place', 'text': p})
    else:
        out = [{'type': 'trend', 'text': t} for t in SearchQuery.objects.values_list('term', flat=True)[:6]]
    return JsonResponse({'suggestions': out})


@login_required
@require_POST
def inquiry_delete(request, pk):
    """Savolni o'chirish.

    Ikki tomon ham o'chira oladi: e'lon EGASI kelgan savolni tozalaydi,
    YUBORUVCHI esa o'zi yozgan xabaridan voz kechadi. Boshqa hech kim emas.
    """
    inq = get_object_or_404(AdInquiry.objects.select_related('ad'), pk=pk)
    if request.user.id not in (inq.ad.user_id, inq.sender_id):
        messages.error(request, "Bu xabarni o'chirish huquqingiz yo'q.")
        return redirect('ad_detail', pk=inq.ad.pk)

    ad_pk = inq.ad.pk
    inq.delete()
    messages.success(request, "Xabar o'chirildi.")
    nxt = request.POST.get('next')
    if nxt == 'inquiries':
        return redirect('my_inquiries')
    return redirect('ad_detail', pk=ad_pk)
