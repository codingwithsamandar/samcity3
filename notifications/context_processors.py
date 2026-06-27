def notifications(request):
    """Navbar uchun o'qilmagan bildirishnomalar soni va so'nggilari."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'notif_unread': 0, 'notif_recent': []}
    qs = user.notifications.all()
    return {
        'notif_unread': qs.filter(is_read=False).count(),
        'notif_recent': list(qs[:8]),
    }
