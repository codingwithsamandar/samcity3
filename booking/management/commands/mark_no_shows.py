"""Belgilangan vaqtda kelinmagan (no-show) bronlarni avtomatik belgilaydi.

Ishga tushirish (masalan har 10 daqiqada cron/scheduled task orqali):
    python manage.py mark_no_shows

Tasdiqlangan (to'langan) bron uchun: agar boshlanish vaqti + joyning kutish
vaqti (grace) o'tib ketgan bo'lsa va xizmat yakunlanmagan bo'lsa — "kelmadi"
holatiga o'tkaziladi va jarima ushlab qolinadi.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from booking.models import VenueBooking


class Command(BaseCommand):
    help = "Vaqtida kelinmagan bronlarni 'kelmadi' (no_show) deb belgilaydi."

    def handle(self, *args, **options):
        now = timezone.now()
        qs = VenueBooking.objects.filter(
            status='confirmed', start_time__isnull=False,
        ).select_related('venue')

        count = 0
        for b in qs:
            starts = b.starts_at
            if starts is None:
                continue
            grace = timedelta(minutes=b.venue.grace_minutes or 0)
            if now > starts + grace:
                b.mark_no_show()
                count += 1

        self.stdout.write(self.style.SUCCESS(f'{count} ta bron "kelmadi" deb belgilandi.'))
