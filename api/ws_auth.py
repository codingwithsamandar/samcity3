"""
WebSocket uchun JWT autentifikatsiya middleware.

Mobil ilova WS ulanishida sessiya cookie bo'lmaydi — token query string orqali
yuboriladi: `ws://.../ws/chat/5/?token=<access_token>`.

Ishlash tartibi (asgi.py da):
    AuthMiddlewareStack(JWTAuthMiddleware(URLRouter(...)))
Sessiya avval ishlaydi (web uchun scope['user'] ni o'rnatadi), keyin bu
middleware token bo'lsa scope['user'] ni JWT foydalanuvchisiga almashtiradi.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        token = self._extract_token(scope)
        if token:
            user = await self._get_user(token)
            if user is not None:
                scope['user'] = user
        return await self.inner(scope, receive, send)

    @staticmethod
    def _extract_token(scope):
        qs = parse_qs(scope.get('query_string', b'').decode())
        if 'token' in qs and qs['token']:
            return qs['token'][0]
        # Header orqali ham qo'llab-quvvatlash (Sec-WebSocket-Protocol / Authorization)
        for name, value in scope.get('headers', []):
            if name == b'authorization':
                raw = value.decode()
                if raw.lower().startswith('bearer '):
                    return raw[7:]
        return None

    @database_sync_to_async
    def _get_user(self, raw_token):
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            data = AccessToken(raw_token)
            User = get_user_model()
            return User.objects.get(id=data['user_id'])
        except Exception:
            return None
