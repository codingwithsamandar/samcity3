"""Liveness va readiness endpointlari (Docker / nginx / monitoring uchun).

- `GET /api/health/`  — liveness: ilova ishlayaptimi (DB'ga tegmaydi, tez).
- `GET /api/ready/`   — readiness: DB va cache/Redis ulanishini tekshiradi.
"""
from django.core.cache import cache
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness — jarayon tirik bo'lsa har doim 200."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        return Response({'status': 'ok'})


class SeedStatusView(APIView):
    """Demo ma'lumotlar holati — bo'limlar bo'yicha yozuvlar soni.

    `GET /api/seed-status/` — brauzerdan ochib, demolar qo'shilganini tekshirasiz.
    Hammasi 0 bo'lsa — seed ishlamagan; sonlar bo'lsa — demo bor.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        counts = {}

        def _c(label, fn):
            try:
                counts[label] = fn()
            except Exception:
                counts[label] = -1  # jadval yo'q / xato

        from django.contrib.auth import get_user_model
        _c('users', lambda: get_user_model().objects.count())
        _c('ads', lambda: __import__('main.models', fromlist=['Ad']).Ad.objects.count())
        _c('mahallas', lambda: __import__('main.models', fromlist=['Neighborhood']).Neighborhood.objects.count())
        _c('polls', lambda: __import__('main.models', fromlist=['Poll']).Poll.objects.count())
        _c('stores', lambda: __import__('delivery.models', fromlist=['Store']).Store.objects.count())
        _c('products', lambda: __import__('delivery.models', fromlist=['Product']).Product.objects.count())
        _c('taxists', lambda: __import__('taxi.models', fromlist=['Taxist']).Taxist.objects.count())
        _c('venues', lambda: __import__('booking.models', fromlist=['Venue']).Venue.objects.count())
        _c('places', lambda: __import__('places.models', fromlist=['Place']).Place.objects.count())

        seeded = any(v > 0 for k, v in counts.items() if k in ('stores', 'ads', 'taxists', 'places'))
        return Response({'seeded': seeded, 'counts': counts})


class ReadyView(APIView):
    """Readiness — DB va cache (Redis) ishlayotgan bo'lsa 200, aks holda 503."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        db_ok = True
        cache_ok = True
        try:
            with connection.cursor() as cur:
                cur.execute('SELECT 1')
                cur.fetchone()
        except Exception:
            db_ok = False
        try:
            cache.set('readycheck', '1', 10)
            cache_ok = cache.get('readycheck') == '1'
        except Exception:
            cache_ok = False

        ok = db_ok and cache_ok
        return Response(
            {
                'status': 'ready' if ok else 'not_ready',
                'db': 'ok' if db_ok else 'down',
                'cache': 'ok' if cache_ok else 'down',
            },
            status=200 if ok else 503,
        )
