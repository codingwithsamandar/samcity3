"""
Delivery real-time signals: broadcast order status changes to the order's
live-tracking WebSocket room. (Customer-facing DB notifications are handled
separately in notifications/signals.py.)
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Order
from .realtime import push_order_status


@receiver(pre_save, sender=Order)
def _order_track_pre(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_track_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._old_track_status = None
    else:
        instance._old_track_status = None


@receiver(post_save, sender=Order)
def _order_track_post(sender, instance, created, **kwargs):
    if created:
        return
    old = getattr(instance, '_old_track_status', None)
    if old is not None and old != instance.status:
        push_order_status(instance)
