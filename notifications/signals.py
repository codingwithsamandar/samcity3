from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import notify

User = get_user_model()


# ── Status o'zgarishini aniqlash uchun eski qiymatni keshlash ────────────────
def _cache_old(sender, instance, field):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            setattr(instance, f'_old_{field}', getattr(old, field))
        except sender.DoesNotExist:
            setattr(instance, f'_old_{field}', None)
    else:
        setattr(instance, f'_old_{field}', None)


# ─────────────────────────────────────────────────────────────────────────────
#  DELIVERY ORDER — holat o'zgarsa xaridorga
# ─────────────────────────────────────────────────────────────────────────────
try:
    from delivery.models import Order, Store

    @receiver(pre_save, sender=Order)
    def _order_pre(sender, instance, **kwargs):
        _cache_old(sender, instance, 'status')

    @receiver(post_save, sender=Order)
    def _order_post(sender, instance, created, **kwargs):
        if created:
            return
        old = getattr(instance, '_old_status', None)
        if old and old != instance.status:
            notify(
                instance.user,
                f"Buyurtmangiz holati yangilandi: {instance.get_status_display()}",
                reverse('delivery:order_detail', args=[instance.id]),
                'order',
            )

    # Yangi do'kon ochilishi — adminlarga (biznes ro'yxatdan o'tish so'rovi)
    @receiver(post_save, sender=Store)
    def _store_post(sender, instance, created, **kwargs):
        if not created:
            return
        for staff in User.objects.filter(is_staff=True):
            notify(
                staff,
                f"Yangi do'kon ro'yxatdan o'tdi: {instance.name}",
                reverse('delivery:store_detail', args=[instance.pk]),
                'business',
            )
except Exception:
    pass


# ─────────────────────────────────────────────────────────────────────────────
#  VENUE BOOKING — yangi bron egaga; holat o'zgarsa mijozga
# ─────────────────────────────────────────────────────────────────────────────
try:
    from booking.models import VenueBooking

    @receiver(pre_save, sender=VenueBooking)
    def _vb_pre(sender, instance, **kwargs):
        _cache_old(sender, instance, 'status')

    @receiver(post_save, sender=VenueBooking)
    def _vb_post(sender, instance, created, **kwargs):
        if created:
            notify(
                instance.venue.owner,
                f"Yangi bron: {instance.venue.name} — {instance.booking_date}",
                reverse('manage_bookings'),
                'booking',
            )
        else:
            old = getattr(instance, '_old_status', None)
            if old and old != instance.status:
                notify(
                    instance.user,
                    f"Bron holati: {instance.venue.name} — {instance.get_status_display()}",
                    reverse('my_venue_bookings'),
                    'booking',
                )
except Exception:
    pass


# ─────────────────────────────────────────────────────────────────────────────
#  TAXI TRIP — yangi so'rov haydovchiga
# ─────────────────────────────────────────────────────────────────────────────
try:
    from taxi.models import Trip

    @receiver(post_save, sender=Trip)
    def _trip_post(sender, instance, created, **kwargs):
        if created and instance.taxist and instance.taxist.user_id:
            notify(
                instance.taxist.user,
                f"Yangi taksi so'rovi: {instance.point_a} → {instance.point_b}",
                reverse('taxi:taxist_manage'),
                'taxi',
            )
except Exception:
    pass


# ─────────────────────────────────────────────────────────────────────────────
#  CHAT MESSAGE — xona a'zolariga
# ─────────────────────────────────────────────────────────────────────────────
try:
    from main.models import ChatMessage

    @receiver(post_save, sender=ChatMessage)
    def _chat_post(sender, instance, created, **kwargs):
        if not created:
            return
        room = instance.room
        try:
            url = reverse('neighborhood_chat_room', args=[room.id])
        except Exception:
            url = ''
        members = room.members.filter(is_approved=True, is_banned=False).exclude(user=instance.user)
        nb_name = getattr(getattr(room, 'neighborhood', None), 'name', 'Mahalla')
        for m in members.select_related('user'):
            notify(m.user, f"{nb_name}: yangi xabar", url, 'chat')
except Exception:
    pass
