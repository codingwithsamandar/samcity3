"""Eski agent yozuvlarini tozalaydi — AgentAuditLog tez o'sadi.

Standart: 90 kundan eski audit yozuvlari o'chiriladi. Bundan tashqari muddati
o'tgan SelectionSet va yakunlangan/muddati o'tgan PendingAction'lar ham tozalanadi
(baza toza bo'lsin). Cron/scheduler orqali kuniga bir marta chaqirilishi mumkin:

    python manage.py cleanup_agent_logs            # 90 kun (standart)
    python manage.py cleanup_agent_logs --days 30
    python manage.py cleanup_agent_logs --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from assistant.models import AgentAuditLog, PendingAction, SelectionSet


class Command(BaseCommand):
    help = "Eski agent audit yozuvlari va muddati o'tgan vaqtinchalik yozuvlarni tozalaydi."

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=90,
                            help='Necha kundan eski audit yozuvlari o\'chirilsin (standart 90).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Faqat sanaydi, o\'chirmaydi.')

    def handle(self, *args, **opts):
        days = max(1, opts['days'])
        dry = opts['dry_run']
        now = timezone.now()
        cutoff = now - timezone.timedelta(days=days)

        old_audit = AgentAuditLog.objects.filter(created_at__lt=cutoff)
        # Ekrandagi ro'yxatlar qisqa umrli — muddati o'tganini saqlashning ma'nosi yo'q.
        stale_sel = SelectionSet.objects.filter(expires_at__lt=now)
        # Yakunlangan yoki muddati o'tgan tasdiqlar (pending emas) — tarixdan eski.
        done_pending = PendingAction.objects.filter(
            expires_at__lt=cutoff).exclude(status='pending')

        counts = {
            'audit': old_audit.count(),
            'selections': stale_sel.count(),
            'pending': done_pending.count(),
        }

        if dry:
            self.stdout.write(self.style.WARNING(
                f"[dry-run] o'chiriladi: {counts['audit']} audit, "
                f"{counts['selections']} ro'yxat, {counts['pending']} tasdiq."))
            return

        old_audit.delete()
        stale_sel.delete()
        done_pending.delete()
        self.stdout.write(self.style.SUCCESS(
            f"Tozalandi: {counts['audit']} audit, {counts['selections']} ro'yxat, "
            f"{counts['pending']} tasdiq ({days} kundan eski)."))
