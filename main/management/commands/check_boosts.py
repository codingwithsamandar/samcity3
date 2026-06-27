import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Ad

class Command(BaseCommand):
    help = 'Deactivates ads that have expired boost periods'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_boosts = Ad.objects.filter(is_boosted=True, boosted_until__lt=now)
        count = expired_boosts.count()
        
        if count > 0:
            expired_boosts.update(is_boosted=False, boosted_until=None)
            self.stdout.write(self.style.SUCCESS(f'Successfully deactivated {count} expired boosts.'))
        else:
            self.stdout.write(self.style.SUCCESS('No expired boosts found.'))
