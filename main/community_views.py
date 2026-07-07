"""Community feature views: Polls, Help Center, and the Mahalla community map."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .utils import validate_file_type, safe_json
from .models import (
    Poll, PollOption, PollVote, PollComment,
    HelpRequest, HelpVolunteer, Neighborhood, ChatMember, ChatAdmin,
    NeighborhoodAnnouncement, CitizenRequest, CITIZEN_REQUEST_TRANSITIONS,
)


def _notify_mahalla(neighborhood, text, url, exclude_user=None):
    """Notify approved members of a mahalla's chat room (best-effort)."""
    if not neighborhood:
        return
    try:
        from notifications.models import notify
        room = getattr(neighborhood, 'chat_room', None)
        if not room:
            return
        members = ChatMember.objects.filter(room=room, is_approved=True, is_banned=False).select_related('user')
        if exclude_user:
            members = members.exclude(user=exclude_user)
        for m in members:
            notify(m.user, text, url, 'system')
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════════════
#  POLLS
# ════════════════════════════════════════════════════════════════════════════

def poll_list(request):
    polls = Poll.objects.select_related('creator', 'neighborhood').prefetch_related('options__votes')
    nb = request.GET.get('mahalla')
    if nb:
        polls = polls.filter(neighborhood_id=nb)
    data = []
    for p in polls[:50]:
        data.append({'poll': p, 'votes': p.total_votes(), 'open': p.is_open})
    return render(request, 'community/poll_list.html', {
        'polls': data,
        'neighborhoods': Neighborhood.objects.all(),
        'current_mahalla': nb or '',
    })


@login_required
def poll_create(request):
    if request.method == 'POST':
        question = request.POST.get('question', '').strip()
        options = [o.strip() for o in request.POST.getlist('options') if o.strip()]
        if not question or len(options) < 2:
            messages.error(request, "Savol va kamida 2 ta variant kiriting.")
            return render(request, 'community/poll_form.html', {'neighborhoods': Neighborhood.objects.all(), 'post': _form_post(request)})
        poll = Poll.objects.create(
            creator=request.user,
            question=question,
            description=request.POST.get('description', '').strip(),
            poll_type=request.POST.get('poll_type', 'single'),
            is_anonymous=('is_anonymous' in request.POST),
            neighborhood_id=request.POST.get('neighborhood') or None,
        )
        days = request.POST.get('expires_days')
        if days and days.isdigit() and int(days) > 0:
            poll.expires_at = timezone.now() + timedelta(days=int(days))
            poll.save(update_fields=['expires_at'])
        for i, text in enumerate(options[:10]):
            PollOption.objects.create(poll=poll, text=text[:200], order=i)
        from django.urls import reverse
        _notify_mahalla(poll.neighborhood, f"Yangi so'rovnoma: {question[:60]}",
                        reverse('poll_detail', args=[poll.id]), exclude_user=request.user)
        messages.success(request, "So'rovnoma yaratildi! ✅")
        return redirect('poll_detail', poll_id=poll.id)
    return render(request, 'community/poll_form.html', {'neighborhoods': Neighborhood.objects.all(), 'post': _form_post(request)})


def poll_detail(request, poll_id):
    poll = get_object_or_404(Poll.objects.select_related('creator', 'neighborhood'), pk=poll_id)
    options = list(poll.options.prefetch_related('votes'))
    total = sum(o.votes.count() for o in options)
    my_votes = set()
    if request.user.is_authenticated:
        my_votes = set(PollVote.objects.filter(option__poll=poll, user=request.user).values_list('option_id', flat=True))
    opt_data = []
    for o in options:
        c = o.votes.count()
        opt_data.append({'opt': o, 'count': c, 'pct': round(c * 100 / total) if total else 0, 'voted': o.id in my_votes})
    comments = poll.comments.select_related('user')
    return render(request, 'community/poll_detail.html', {
        'poll': poll, 'options': opt_data, 'total': total,
        'has_voted': bool(my_votes), 'comments': comments,
    })


@login_required
def poll_vote(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    if request.method != 'POST':
        return redirect('poll_detail', poll_id=poll.id)
    if not poll.is_open:
        messages.error(request, "So'rovnoma yopilgan.")
        return redirect('poll_detail', poll_id=poll.id)

    option_ids = request.POST.getlist('option')
    valid_ids = set(str(o.id) for o in poll.options.all())
    chosen = [oid for oid in option_ids if oid in valid_ids]
    if not chosen:
        messages.error(request, "Variant tanlang.")
        return redirect('poll_detail', poll_id=poll.id)

    if poll.poll_type == 'single':
        chosen = chosen[:1]
        PollVote.objects.filter(option__poll=poll, user=request.user).delete()
    else:
        # multiple: reset then re-add the current selection
        PollVote.objects.filter(option__poll=poll, user=request.user).delete()

    for oid in chosen:
        PollVote.objects.get_or_create(option_id=oid, user=request.user)
    messages.success(request, "Ovozingiz qabul qilindi. ✅")
    return redirect('poll_detail', poll_id=poll.id)


@login_required
def poll_comment(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            PollComment.objects.create(poll=poll, user=request.user, text=text[:1000])
    return redirect('poll_detail', poll_id=poll.id)


# ════════════════════════════════════════════════════════════════════════════
#  HELP CENTER
# ════════════════════════════════════════════════════════════════════════════

def help_list(request):
    qs = HelpRequest.objects.select_related('creator', 'neighborhood').prefetch_related('volunteers')
    cat = request.GET.get('category', '')
    kind = request.GET.get('kind', '')
    status = request.GET.get('status', 'open')
    if cat:
        qs = qs.filter(category=cat)
    if kind:
        qs = qs.filter(kind=kind)
    if status:
        qs = qs.filter(status=status)
    return render(request, 'community/help_list.html', {
        'requests': qs[:60],
        'categories': HelpRequest.CATEGORY_CHOICES,
        'cur_cat': cat, 'cur_kind': kind, 'cur_status': status,
    })


@login_required
def _form_post(request):
    """Forma qiymatlari: yo'q kalit '' (template crash bo'lmasligi uchun)."""
    from collections import defaultdict
    d = defaultdict(str)
    if request.method == 'POST':
        d.update(request.POST.dict())
    return d


def help_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        if not title or not description:
            messages.error(request, "Sarlavha va tavsif majburiy.")
            return render(request, 'community/help_form.html', {
                'categories': HelpRequest.CATEGORY_CHOICES, 'kinds': HelpRequest.KIND_CHOICES,
                'neighborhoods': Neighborhood.objects.all(), 'post': _form_post(request),
            })
        req = HelpRequest.objects.create(
            creator=request.user, title=title, description=description,
            kind=request.POST.get('kind', 'request'),
            category=request.POST.get('category', 'general'),
            location=request.POST.get('location', '').strip(),
            phone=request.POST.get('phone', '').strip(),
            neighborhood_id=request.POST.get('neighborhood') or None,
            is_urgent=('is_urgent' in request.POST),
        )
        help_image = request.FILES.get('image')
        if help_image:
            try:
                validate_file_type(help_image)
                req.image = help_image
            except Exception as e:
                messages.error(request, f"Rasm: {str(e)}")
            req.save(update_fields=['image'])
        from django.urls import reverse
        _notify_mahalla(req.neighborhood, f"Yangi yordam so'rovi: {title[:50]}",
                        reverse('help_detail', args=[req.id]), exclude_user=request.user)
        messages.success(request, "So'rov e'lon qilindi! ✅")
        return redirect('help_detail', req_id=req.id)
    return render(request, 'community/help_form.html', {
        'categories': HelpRequest.CATEGORY_CHOICES, 'kinds': HelpRequest.KIND_CHOICES,
        'neighborhoods': Neighborhood.objects.all(), 'post': _form_post(request),
    })


def help_detail(request, req_id):
    req = get_object_or_404(
        HelpRequest.objects.select_related('creator', 'neighborhood').prefetch_related('volunteers__user'),
        pk=req_id,
    )
    is_volunteer = False
    if request.user.is_authenticated:
        is_volunteer = req.volunteers.filter(user=request.user).exists()
    return render(request, 'community/help_detail.html', {
        'req': req, 'is_volunteer': is_volunteer, 'is_owner': request.user == req.creator,
    })


@login_required
def help_volunteer(request, req_id):
    req = get_object_or_404(HelpRequest, pk=req_id)
    if request.method == 'POST':
        _, created = HelpVolunteer.objects.get_or_create(
            request=req, user=request.user,
            defaults={'message': request.POST.get('message', '').strip()[:300]},
        )
        if created:
            try:
                from notifications.models import notify
                from django.urls import reverse
                notify(req.creator, f"Ko'ngilli yordam taklif qildi: {req.title[:40]}",
                       reverse('help_detail', args=[req.id]), 'system')
            except Exception:
                pass
            messages.success(request, "Rahmat! Siz ko'ngilli sifatida ro'yxatga olindingiz. 🙏")
        else:
            messages.info(request, "Siz allaqachon ko'ngillisiz.")
    return redirect('help_detail', req_id=req.id)


@login_required
def help_status(request, req_id):
    req = get_object_or_404(HelpRequest, pk=req_id, creator=request.user)
    if request.method == 'POST':
        new = request.POST.get('status', '')
        if new in dict(HelpRequest.STATUS_CHOICES):
            req.status = new
            req.save(update_fields=['status'])
            messages.success(request, "Holat yangilandi.")
    return redirect('help_detail', req_id=req.id)


# ════════════════════════════════════════════════════════════════════════════
#  MAHALLA COMMUNITY MAP
# ════════════════════════════════════════════════════════════════════════════

def community_map(request):
    """Mahalla xaritasi — faqat foydalanuvchining o'z mahallasini ko'rsatadi."""
    import json
    my = None
    if request.user.is_authenticated and request.user.neighborhood_id:
        n = request.user.neighborhood
        if n and n.boundary:
            my = {
                'id': n.pk,
                'name': n.name,
                'color': n.color or '#3551d1',
                'boundary': n.boundary,
                'center': n.centroid(),
                'description': n.description,
            }
    return render(request, 'community/mahalla_map.html', {
        'my_neighborhood_json': safe_json(my),
        'has_my_neighborhood': my is not None,
    })


def community_map_geojson(request):
    """Birlashtirilgan xarita: joylar + yordam so'rovlari + favqulodda holatlar."""
    from places.models import Place
    markers = []

    for p in Place.objects.filter(is_active=True).only(
            'id', 'name', 'category', 'latitude', 'longitude', 'address'):
        markers.append({
            'type': 'place', 'category': p.category, 'icon': p.icon,
            'name': p.name, 'lat': p.latitude, 'lng': p.longitude,
            'address': p.address, 'cat': p.get_category_display(),
            'url': reverse('places:place_detail', args=[p.id]),
        })

    helps = HelpRequest.objects.filter(
        status__in=['open', 'in_progress'], latitude__isnull=False, longitude__isnull=False,
    ).only('id', 'title', 'category', 'is_urgent', 'latitude', 'longitude', 'location')
    for h in helps:
        emergency = h.category == 'emergency' or h.is_urgent
        markers.append({
            'type': 'emergency' if emergency else 'help',
            'category': 'emergency' if emergency else 'help',
            'icon': '🚨' if emergency else '🤝',
            'name': h.title, 'lat': h.latitude, 'lng': h.longitude,
            'address': h.location, 'cat': h.get_category_display(),
            'url': reverse('help_detail', args=[h.id]),
        })

    return JsonResponse({'markers': markers})


# ════════════════════════════════════════════════════════════════════════════
#  MAHALLA SAHIFASI (yagona: ma'lumot, e'lonlar, joylar, xarita, chat, murojaat)
# ════════════════════════════════════════════════════════════════════════════

# Joy toifalarini "mahalla" ko'rinishida guruhlash tartibi (do'kon alohida).
_PLACE_GROUP_ORDER = [
    'barber', 'school', 'kindergarten', 'government', 'hospital', 'pharmacy',
    'bank', 'post', 'restaurant', 'organization',
]


def _stores_in(neighborhood):
    """Shu mahallaga tegishli MAHALLA do'konlari (store_type='mahalla', FK bo'yicha).

    Yetkazib beruvchi do'konlar bu yerda ko'rinmaydi — ular faqat /delivery/ da.
    """
    try:
        from delivery.models import Store
    except Exception:
        return []
    return list(
        Store.objects.filter(
            is_active=True, store_type='mahalla', neighborhood=neighborhood,
        ).select_related('category')
    )


def _places_in_grouped(neighborhood):
    """Mahalla ichidagi joylarni toifa bo'yicha guruhlaydi (do'kon toifasidan tashqari)."""
    from places.models import Place, CATEGORY_CHOICES
    labels = dict(CATEGORY_CHOICES)
    inside = [p for p in Place.objects.filter(is_active=True)
              if p.category != 'delivery_store' and neighborhood.contains_point(p.latitude, p.longitude)]
    by_cat = {}
    for p in inside:
        by_cat.setdefault(p.category, []).append(p)
    # Belgilangan tartibda, keyin qolganlar
    ordered = []
    seen = set()
    for cat in _PLACE_GROUP_ORDER:
        if cat in by_cat:
            ordered.append({'key': cat, 'label': labels.get(cat, cat), 'items': by_cat[cat]})
            seen.add(cat)
    for cat, items in by_cat.items():
        if cat not in seen:
            ordered.append({'key': cat, 'label': labels.get(cat, cat), 'items': items})
    return ordered


def _notify_neighborhood_admins(neighborhood, text, url, exclude_user=None):
    """Mahalla adminlariga (ChatAdmin + staff emas — faqat tayinlangan raislar) xabar."""
    try:
        from notifications.models import notify
        admins = ChatAdmin.objects.filter(neighborhood=neighborhood).select_related('user')
        for a in admins:
            if exclude_user and a.user_id == exclude_user.id:
                continue
            notify(a.user, text, url, 'system')
    except Exception:
        pass


def mahalla_home(request):
    """Mahalla bo'limi kirish nuqtasi — avval mahalla TANLASH oynasi ko'rsatiladi.

    Foydalanuvchi o'z mahallasini (yoki boshqasini) tanlab, so'ng sahifaga o'tadi.
    """
    my_id = request.user.neighborhood_id if request.user.is_authenticated else None
    return render(request, 'community/mahalla_home.html', {
        'neighborhoods': Neighborhood.objects.all(),
        'my_neighborhood_id': my_id,
    })


def mahalla_detail(request, pk):
    """Yagona Mahalla sahifasi (tab'lar: ma'lumot, e'lonlar, joylar, xarita, chat, murojaat)."""
    import json
    neighborhood = get_object_or_404(Neighborhood, pk=pk)
    is_admin = neighborhood.is_admin(request.user)
    room = getattr(neighborhood, 'chat_room', None)

    # Murojaatlar: admin barchani, oddiy foydalanuvchi faqat o'zinikini ko'radi.
    if is_admin:
        requests_qs = neighborhood.citizen_requests.select_related('user')[:100]
    elif request.user.is_authenticated:
        requests_qs = neighborhood.citizen_requests.filter(user=request.user)[:50]
    else:
        requests_qs = neighborhood.citizen_requests.none()

    # Mahalla do'kon arizalari — faqat admin ko'radi (tasdiqlash/rad etish uchun).
    store_requests = []
    if is_admin:
        store_requests = list(
            neighborhood.store_requests.filter(status='pending').select_related('user'))

    # Foydalanuvchi shu mahalla do'koni egasimi — "Do'kon egasi paneli" havolasi uchun.
    owns_store = False
    if request.user.is_authenticated:
        from delivery.models import Store
        owns_store = Store.objects.filter(
            owner=request.user, store_type='mahalla', neighborhood=neighborhood).exists()

    # ── So'rovnomalar (shu mahallaga tegishli) ──
    polls_qs = (Poll.objects.filter(neighborhood=neighborhood, is_active=True)
                .select_related('creator').prefetch_related('options__votes'))
    my_poll_votes = set()
    if request.user.is_authenticated:
        my_poll_votes = set(PollVote.objects.filter(
            option__poll__neighborhood=neighborhood, user=request.user
        ).values_list('option_id', flat=True))
    polls_data = []
    for p in polls_qs[:30]:
        opts = list(p.options.all())
        total = sum(o.votes.count() for o in opts)
        opt_data = [{
            'opt': o, 'count': o.votes.count(),
            'pct': round(o.votes.count() * 100 / total) if total else 0,
            'voted': o.id in my_poll_votes,
        } for o in opts]
        polls_data.append({
            'poll': p, 'options': opt_data, 'total': total,
            'has_voted': any(od['voted'] for od in opt_data),
        })

    # ── Valentyorlik / yordam (shu mahallaga tegishli) ──
    help_requests = (HelpRequest.objects.filter(neighborhood=neighborhood)
                     .select_related('creator')[:40])

    # ── Dashboard uchun so'nggi chat xabarlari ──
    chat_messages = []
    if room is not None:
        chat_messages = list(
            room.messages.select_related('user').order_by('-created_at')[:4])
        chat_messages.reverse()

    return render(request, 'community/mahalla_detail.html', {
        'chat_messages': chat_messages,
        'neighborhood': neighborhood,
        'is_admin': is_admin,
        'owns_store': owns_store,
        'announcements': neighborhood.announcements.select_related('created_by')[:30],
        'stores': _stores_in(neighborhood),
        'store_requests': store_requests,
        'place_groups': _places_in_grouped(neighborhood),
        'polls_data': polls_data,
        'help_requests': help_requests,
        'chat_room': room,
        'requests': requests_qs,
        'req_categories': CitizenRequest.CATEGORY_CHOICES,
        'req_statuses': CitizenRequest.STATUS_CHOICES,
        'has_boundary': bool(neighborhood.boundary),
        # Xarita: chegara CHIZILMAGAN bo'lsa ham, markaz koordinatasi bo'lsa
        # xarita ko'rsatiladi (mahalla tanlangach xarita chiqishi uchun).
        'has_map': bool(neighborhood.centroid()),
        'boundary_json': safe_json(neighborhood.boundary or []),
        'centroid_json': safe_json(neighborhood.centroid()),
    })


@login_required
def announcement_create(request, pk):
    """Mahalla raisi/admin rasmiy e'lon joylaydi (+ mahalla a'zolariga bildirishnoma)."""
    neighborhood = get_object_or_404(Neighborhood, pk=pk)
    if not neighborhood.is_admin(request.user):
        messages.error(request, "E'lon joylash faqat mahalla admini uchun.")
        return redirect('mahalla_detail', pk=pk)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        text = request.POST.get('text', '').strip()
        if not title or not text:
            messages.error(request, "Sarlavha va matn majburiy.")
            return redirect('mahalla_detail', pk=pk)
        ann = NeighborhoodAnnouncement(
            neighborhood=neighborhood, title=title, text=text, created_by=request.user)
        img = request.FILES.get('image')
        if img:
            try:
                validate_file_type(img)
                ann.image = img
            except Exception as e:
                messages.warning(request, f"Rasm: {str(e)}")
        ann.save()
        _notify_mahalla(neighborhood, f"📢 Mahalla e'loni: {title[:60]}",
                        reverse('mahalla_detail', args=[pk]), exclude_user=request.user)
        messages.success(request, "E'lon joylandi! ✅")
    return redirect('mahalla_detail', pk=pk)


@login_required
def citizen_request_create(request, pk):
    """Fuqaro murojaat/shikoyat yuboradi (+ mahalla adminlariga bildirishnoma)."""
    neighborhood = get_object_or_404(Neighborhood, pk=pk)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        text = request.POST.get('text', '').strip()
        category = request.POST.get('category', 'other')
        if not title or not text:
            messages.error(request, "Mavzu va matn majburiy.")
            return redirect('mahalla_detail', pk=pk)
        if category not in dict(CitizenRequest.CATEGORY_CHOICES):
            category = 'other'
        req = CitizenRequest(
            neighborhood=neighborhood, user=request.user,
            category=category, title=title, text=text)
        img = request.FILES.get('image')
        if img:
            try:
                validate_file_type(img)
                req.image = img
            except Exception as e:
                messages.warning(request, f"Rasm: {str(e)}")
        req.save()
        _notify_neighborhood_admins(
            neighborhood, f"🗣 Yangi murojaat: {title[:50]}",
            reverse('mahalla_detail', args=[pk]), exclude_user=request.user)
        messages.success(request, "Murojaatingiz yuborildi! Holatini shu yerda kuzatasiz. ✅")
    return redirect('mahalla_detail', pk=pk)


@login_required
def citizen_request_status(request, req_id):
    """Mahalla admini murojaat holatini o'zgartiradi + javob yozadi (+ mijozga bildirishnoma)."""
    req = get_object_or_404(CitizenRequest.objects.select_related('neighborhood', 'user'), pk=req_id)
    neighborhood = req.neighborhood
    if not (neighborhood and neighborhood.is_admin(request.user)):
        messages.error(request, "Murojaatni boshqarish faqat mahalla admini uchun.")
        return redirect('mahalla_detail', pk=neighborhood.pk if neighborhood else '')
    if request.method == 'POST':
        new_status = request.POST.get('status', '')
        response = request.POST.get('response', '').strip()
        changed = False
        if new_status and new_status != req.status:
            if new_status in CITIZEN_REQUEST_TRANSITIONS.get(req.status, set()):
                req.status = new_status
                req.responded_by = request.user
                changed = True
            else:
                messages.error(request, "Bu holatga o'tib bo'lmaydi.")
        if response:
            req.response = response
            req.responded_by = request.user
            changed = True
        if changed:
            req.save()
            try:
                from notifications.models import notify
                notify(req.user, f"Murojaatingiz holati: {req.get_status_display()}",
                       reverse('mahalla_detail', args=[neighborhood.pk]), 'system')
            except Exception:
                pass
            messages.success(request, "Murojaat yangilandi.")
    return redirect('mahalla_detail', pk=neighborhood.pk)
