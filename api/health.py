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
