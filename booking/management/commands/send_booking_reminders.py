"""Bron eslatmalari — yaqinlashayotgan bronlar uchun mijozga bildirishnoma.

Ishlatish (cron/scheduler bilan har 10-15 daqiqada):
    python manage.py send_booking_reminders            # default: 2 soat oldin
    python manage.py send_booking_reminders --hours 3

Mantiq: status pending/confirmed, boshlanishiga <= N soat qolgan (lekin hali
o'tmagan), eslatma yuborilmagan bronlar topiladi → notify() (WebSocket + FCM
push, sozlangan bo'lsa) → reminder_sent_at belgilanadi (takror yubormaslik).
start_time'siz (kunlik, masalan to'yxona) bronlar uchun eslatma bron kunining
ertalabida (sana bugungi bo'lsa) yuboriladi.
"""
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from booking.models import VenueBooking
from notifications.models import notify


class Command(BaseCommand):
    help = "Yaqinlashayotgan venue bronlari uchun mijozlarga eslatma yuboradi."

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours', type=int, default=2,
            help='Boshlanishiga necha soat qolganda eslatilsin (default: 2).',
        )

    def handle(self, *args, **options):
        hours = max(options['hours'], 1)
        now = timezone.localtime()
        horizon = now + timedelta(hours=hours)

        qs = (
            VenueBooking.objects
            .filter(
                status__in=('pending', 'confirmed'),
                reminder_sent_at__isnull=True,
                booking_date__gte=now.date(),
                booking_date__lte=horizon.date(),
            )
            .select_related('venue', 'user')
        )

        sent = 0
        for booking in qs:
            if booking.start_time:
                starts = timezone.make_aware(
                    datetime.combine(booking.booking_date, booking.start_time)
                )
                # Hali boshlanmagan va N soat ichida boshlanadigan bronlar.
                if not (now <= starts <= horizon):
                    continue
                when = starts.strftime('%H:%M')
                text = f"Eslatma: bugun {when} da «{booking.venue.name}» da broningiz bor."
            else:
                # Kunlik bron (to'yxona) — bron kuni yetib kelganda bir marta.
                if booking.booking_date != now.date():
                    continue
                text = f"Eslatma: bugun «{booking.venue.name}» da broningiz bor."

            notify(booking.user, text, url='/booking/my/', category='booking')
            booking.reminder_sent_at = timezone.now()
            booking.save(update_fields=['reminder_sent_at'])
            sent += 1

        self.stdout.write(self.style.SUCCESS(f'Yuborilgan eslatmalar: {sent}'))
