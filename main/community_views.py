"""Community feature views: Polls, Help Center, and the Mahalla community map."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .utils import validate_file_type
from .models import (
    Poll, PollOption, PollVote, PollComment,
    HelpRequest, HelpVolunteer, Neighborhood, ChatMember,
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
        'my_neighborhood_json': json.dumps(my),
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
