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

    # Do'kon egasiga qaysi holatlar haqida xabar beriladi. `accepted`,
    # `preparing`, `ready` — egasining O'ZI bosgan tugmalari, ular yuborilmaydi
    # (aks holda har bosishda o'ziga xabar kelardi).
    OWNER_STATUS_TEXT = {
        'assigned': "Buyurtmani kuryer oldi 🚗",
        'picked_up': "Kuryer buyurtmani do'kondan oldi 📦",
        'on_the_way': "Kuryer buyurtma bilan yo'lga chiqdi 🛵",
        'delivered': "Buyurtma mijozga yetkazildi ✅",
        'cancelled': "Buyurtma bekor qilindi ❌",
    }
    # Olib ketishda kuryer yo'q — «yetkazildi» aslida mijoz o'zi olib ketgani.
    OWNER_PICKUP_TEXT = {
        'delivered': "Mijoz buyurtmani olib ketdi ✅",
        'cancelled': "Buyurtma bekor qilindi ❌",
    }

    def _order_owner(order):
        """Buyurtma tegishli do'kon egasi.

        Buyurtma checkout'da do'kon bo'yicha bo'linadi, ya'ni bitta buyurtma —
        bitta do'kon. Mahsulot o'chirilgan bo'lsa (`product` SET_NULL) egasini
        topib bo'lmaydi — bunday holda None qaytadi va xabar o'tkazib yuboriladi.
        """
        item = (order.items.select_related('product__store__owner')
                .filter(product__isnull=False).first())
        return item.product.store.owner if item else None

    @receiver(post_save, sender=Order)
    def _order_post(sender, instance, created, **kwargs):
        if created:
            return
        old = getattr(instance, '_old_status', None)
        if not old or old == instance.status:
            return
        notify(
            instance.user,
            f"Buyurtmangiz holati yangilandi: {instance.get_status_display()}",
            reverse('delivery:order_detail', args=[instance.id]),
            'order',
        )
        # ── Do'kon egasiga ham: buyurtma uning qo'lidan chiqqach nima
        # bo'layotganini bilishi kerak. Avval faqat xaridor xabar olardi,
        # shuning uchun kuryer mahsulotni olib ketganini egasi bilmasdi.
        table = (OWNER_PICKUP_TEXT if instance.fulfillment_type == 'pickup'
                 else OWNER_STATUS_TEXT)
        text = table.get(instance.status)
        if not text:
            return
        owner = _order_owner(instance)
        # Egasi o'z do'konidan buyurtma bergan bo'lsa — ikki xabar kelmasin.
        if owner is None or owner.id == instance.user_id:
            return
        short = str(instance.id)[:8]
        notify(owner, f"#{short} — {text}", reverse('delivery:store_orders'), 'order')

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
    from django.conf import settings as _settings
    from taxi.models import Trip

    @receiver(post_save, sender=Trip)
    def _trip_post(sender, instance, created, **kwargs):
        # Taksi arxivlangan — yo'llar ulanmagani uchun reverse() qilinmaydi.
        if not _settings.TAXI_ENABLED:
            return
        if created and instance.taxist and instance.taxist.user_id:
            notify(
                instance.taxist.user,
                f"Yangi taksi so'rovi: {instance.point_a} → {instance.point_b}",
                reverse('taxi:taxist_manage'),
                'taxi',
            )
except Exception:
    pass
