from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .models import Notification


@login_required
def notification_list(request):
    qs = request.user.notifications.all()
    return render(request, 'notifications/notification_list.html', {'notifications': qs})


@login_required
def notification_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=['is_read'])
    return redirect(n.url or 'notification_list')


@login_required
def notification_read_all(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('notification_list')
