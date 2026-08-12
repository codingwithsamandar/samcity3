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
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

from . import service, stt as stt_mod, tts as tts_mod


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
    voice = bool(body.get('voice'))

    res = service.build_response(message, location=location, history=history,
                                 context=context, request=request, voice=voice)
    return JsonResponse(res)


@require_POST
def tts(request):
    """POST /ai/tts/  {text}  →  audio/mpeg (bulut sozlangan bo'lsa) yoki 204.

    204 → server TTS o'chiq/ishlamadi; widget brauzer ovoziga qaytadi.
    """
    if _rate_limited(request):
        return JsonResponse({'ok': False, 'error': 'rate_limited'}, status=429)
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'bad_json'}, status=400)
    text = (body.get('text') or '').strip()
    if not text:
        return JsonResponse({'ok': False, 'error': 'empty'}, status=400)

    audio = tts_mod.synthesize(text)
    if not audio:
        return HttpResponse(status=204)
    resp = HttpResponse(audio, content_type=tts_mod.content_type())
    resp['Cache-Control'] = 'private, max-age=86400'
    return resp


@require_POST
def stt(request):
    """POST /ai/stt/  (audio)  →  {text} (server STT bo'lsa) yoki 204.

    204 → server STT o'chiq/tanimadi; widget brauzer Web Speech'ga qaytadi
    (tts.py dagi bir xil «muloyim degradatsiya» naqshi). Mohir.ai ulangach
    shu endpoint o'zgarmasdan matn qaytara boshlaydi.

    Audio ikki yo'l bilan kelishi mumkin: xom tana (Content-Type: audio/*) yoki
    multipart `audio` fayli.
    """
    if _rate_limited(request):
        return JsonResponse({'ok': False, 'error': 'rate_limited'}, status=429)

    audio, ctype = _read_audio(request)
    lang = (request.GET.get('lang') or request.POST.get('lang') or 'uz').strip()

    text = stt_mod.transcribe(audio, lang=lang, content_type=ctype)
    if not text:
        # 204 + tayyorlik sar'lavhasi. Widget shu sarlavhani o'qib mic yo'lini
        # tanlaydi: '1' → server STT (MediaRecorder yuboradi), '0' → brauzer
        # Web Speech. Mohir ulangач is_enabled() True bo'ladi va widget
        # O'ZGARMASDAN server STT'ga o'tadi.
        resp = HttpResponse(status=204)
        resp['X-STT-Available'] = '1' if stt_mod.is_enabled() else '0'
        return resp
    return JsonResponse({'ok': True, 'text': text})


def _read_audio(request):
    """So'rovdan audio baytlarini oladi: multipart `audio` yoki xom tana."""
    f = request.FILES.get('audio')
    if f is not None:
        return f.read(), (f.content_type or '')
    ctype = request.META.get('CONTENT_TYPE', '')
    if ctype.startswith('audio/'):
        return request.body, ctype
    return b'', ctype


@ensure_csrf_cookie
def page(request):
    """Ixtiyoriy to'liq sahifa (/ai/) — widget bilan bir xil oqim, alohida ochiladi."""
    return render(request, 'assistant/page.html')


# ─── Tasdiq oqimi — LLM YARATgan, foydalanuvchi TASDIQlaydigan amal ────────────
# CSRF: bu endpoint'lar sessiyali web uchun CSRF talab qiladi (default himoya —
# csrf_exempt QILINMAYDI). Widget X-CSRFToken sarlavhasi bilan yuboradi.

def _confirm_common(request, action_id, fn):
    """confirm/cancel uchun umumiy qobiq: rate-limit, auth, JSON javob."""
    if _rate_limited(request):
        return JsonResponse({'ok': False, 'error': 'rate_limited',
                             'reply': "Biroz sekinroq 🙂"}, status=429)
    if not request.user.is_authenticated:
        # Egalikni oshkor qilmaslik uchun 404 (403 emas).
        return JsonResponse({'ok': False, 'error': 'not_found',
                             'reply': "Bunday amal topilmadi."}, status=404)
    out = fn(str(action_id), request.user)
    http_status = out.get('status', 200 if out.get('ok') else 400)
    payload = {'ok': out.get('ok', False), 'reply': out.get('reply', '')}
    if out.get('result') is not None:
        payload['result'] = out['result']
    if out.get('pending_id'):
        payload['pending_id'] = out['pending_id']
    return JsonResponse(payload, status=http_status if not out.get('ok') else 200)


@require_POST
def confirm_action(request, action_id):
    """POST /ai/confirm/<uuid>/ — tasdiqlangan amalni bajaradi (idempotent)."""
    from . import confirm
    return _confirm_common(request, action_id, confirm.execute)


@require_POST
def cancel_action(request, action_id):
    """POST /ai/cancel/<uuid>/ — tasdiq kutayotgan amalni bekor qiladi."""
    from . import confirm
    return _confirm_common(request, action_id, confirm.cancel)
