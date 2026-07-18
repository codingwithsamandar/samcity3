"""AI yordamchi — chat endpoint (JSON) va alohida sahifa.

Gibrid oqim:
  1) Mahalliy dvigatel (engine.handle) savolni tahlil qiladi.
  2) Agar intent 'unknown' bo'lsa VA LLM sozlangan bo'lsa (AI_API_KEY) —
     llm.ask() ga uzatiladi.
  3) LLM ham javob bermasa — muloyim "tushunmadim" javobi qaytariladi.
"""

import json
import os

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

from . import service


# ── So'rov cheklovi (throttling) — server barqarorligi + suiiste'mol himoyasi ─
# Bir foydalanuvchi (IP) daqiqasiga eng ko'pi RATE_LIMIT ta so'rov yuborishi mumkin.
# Env orqali sozlanadi. Cache (LocMem yoki Redis) orqali sanaladi.
RATE_LIMIT = int(os.environ.get('AI_RATE_LIMIT', '30'))
RATE_WINDOW = int(os.environ.get('AI_RATE_WINDOW', '60'))  # soniya


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '?')


def _rate_limited(request):
    """True — agar limit oshib ketgan bo'lsa. Cache xatosi bo'lsa — bloklamaymiz."""
    if RATE_LIMIT <= 0:
        return False
    key = f'ai_rl:{_client_ip(request)}'
    try:
        count = cache.get(key, 0)
        if count >= RATE_LIMIT:
            return True
        cache.set(key, count + 1, RATE_WINDOW)
    except Exception:
        return False
    return False


def _parse_location(raw):
    """Kiruvchi joylashuvni (lat, lng) ga aylantiradi yoki None."""
    if not isinstance(raw, dict):
        return None
    try:
        lat = float(raw.get('lat'))
        lng = float(raw.get('lng'))
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return (lat, lng)


@require_POST
def chat(request):
    """POST /ai/chat/  →  {message, location?, history?}  ->  JSON javob."""
    if _rate_limited(request):
        return JsonResponse({
            'ok': False, 'error': 'rate_limited',
            'reply': ("Biroz sekinroq 🙂 Juda ko'p so'rov yubordingiz. "
                      "Bir daqiqadan so'ng qayta urinib ko'ring."),
        }, status=429)
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'bad_json'}, status=400)

    message = (body.get('message') or '').strip()
    if not message:
        return JsonResponse({'ok': False, 'error': 'empty'}, status=400)
    if len(message) > 1000:
        message = message[:1000]

    location = _parse_location(body.get('location'))
    history = body.get('history') if isinstance(body.get('history'), list) else None
    context = body.get('context') if isinstance(body.get('context'), dict) else None

    res = service.build_response(message, location=location, history=history, context=context)
    return JsonResponse(res)


@ensure_csrf_cookie
def page(request):
    """Ixtiyoriy to'liq sahifa (/ai/) — widget bilan bir xil oqim, alohida ochiladi."""
    return render(request, 'assistant/page.html')
