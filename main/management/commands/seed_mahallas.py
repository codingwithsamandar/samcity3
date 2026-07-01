"""Shofirkon shahrini mahallalarga bo'lib, demo chegaralar yaratadi.

Aniq rasmiy chegara ma'lumotlari ochiq emas, shuning uchun shahar markazi
atrofida gap/overlapsiz organik ko'rinishdagi poligon to'ri (grid) generatsiya
qilinadi. Har bir katak — bitta mahalla. Adminda chegara/nom keyin tahrirlanadi.

    python manage.py seed_mahallas          # yo'q bo'lsa yaratadi
    python manage.py seed_mahallas --reset  # demo mahallalarni qayta quradi
"""
import random
from django.core.management.base import BaseCommand
from django.db import transaction
from main.models import Neighborhood, ChatRoom

# Shofirkon shahri markazi (places.views.CENTER bilan bir xil).
CENTER_LAT, CENTER_LNG = 40.1156, 64.5036

# Mahalla nomlari (demo — Shofirkon hududiga mos uslubda).
NAMES = [
    "Shofirkon markaz", "Guliston", "Navbahor",
    "Yangiobod", "Do'stlik", "Bunyodkor",
    "Istiqlol", "Obod", "Chashma",
]
COLORS = [
    "#e0a52e", "#3551d1", "#0ea371", "#e5484d", "#8b5cf6",
    "#0891b2", "#d946a0", "#65a30d", "#f97316",
]


class Command(BaseCommand):
    help = "Shofirkon shahrini demo mahallalarga bo'ladi (xarita chegaralari bilan)."

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help="Avval demo mahallalarni o'chirib, qaytadan yaratadi.")
        parser.add_argument('--rows', type=int, default=3)
        parser.add_argument('--cols', type=int, default=3)

    @transaction.atomic
    def handle(self, *args, **opts):
        rows, cols = opts['rows'], opts['cols']
        rng = random.Random(42)  # barqaror (deterministik) jitter

        # Shahar atrofidagi qamrov (taxminan 4.5km x 4.5km).
        span_lat, span_lng = 0.042, 0.052
        lat_top = CENTER_LAT + span_lat / 2
        lng_left = CENTER_LNG - span_lng / 2
        d_lat = span_lat / rows
        d_lng = span_lng / cols

        # Umumiy tugun (vertex) to'ri — qo'shni kataklar bir tugunni ulashadi,
        # shuning uchun chegaralarda bo'shliq/ustma-ustlik bo'lmaydi.
        jitter_lat = d_lat * 0.16
        jitter_lng = d_lng * 0.16
        verts = []
        for r in range(rows + 1):
            line = []
            for c in range(cols + 1):
                lat = lat_top - r * d_lat
                lng = lng_left + c * d_lng
                # Tashqi chekka tugunlar deyarli tekis, ichki tugunlar organik.
                if 0 < r < rows:
                    lat += rng.uniform(-jitter_lat, jitter_lat)
                if 0 < c < cols:
                    lng += rng.uniform(-jitter_lng, jitter_lng)
                line.append([round(lat, 6), round(lng, 6)])
            verts.append(line)

        if opts['reset']:
            deleted = Neighborhood.objects.filter(name__in=NAMES).delete()
            self.stdout.write(self.style.WARNING(f"Reset: {deleted[0]} obyekt o'chirildi."))

        created = updated = 0
        idx = 0
        for r in range(rows):
            for c in range(cols):
                if idx >= len(NAMES):
                    break
                name = NAMES[idx]
                color = COLORS[idx % len(COLORS)]
                ring = [
                    verts[r][c], verts[r][c + 1],
                    verts[r + 1][c + 1], verts[r + 1][c],
                ]
                clat = sum(p[0] for p in ring) / 4
                clng = sum(p[1] for p in ring) / 4

                obj, was_created = Neighborhood.objects.get_or_create(name=name)
                obj.boundary = ring
                obj.center_lat = round(clat, 6)
                obj.center_lng = round(clng, 6)
                obj.color = color
                if was_created and not obj.description:
                    obj.description = f"{name} mahallasi — Shofirkon shahri."
                obj.save()
                ChatRoom.objects.get_or_create(neighborhood=obj)
                created += int(was_created)
                updated += int(not was_created)
                idx += 1

        self.stdout.write(self.style.SUCCESS(
            f"Tayyor: {created} ta yangi, {updated} ta yangilangan mahalla "
            f"(chegaralar bilan). Jami nomlar: {idx}."))
