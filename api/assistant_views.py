"""AI yordamchi — mobil REST API (Flutter ilova).

`POST /api/assistant/chat/`
    Body: {
        "message":  "menga eng yaqin dorixona",   (majburiy)
        "location": {"lat": 40.11, "lng": 64.50},  (ixtiyoriy — aniqroq natija)
        "history":  [{"role":"user","content":"..."}],  (ixtiyoriy — LLM konteksti)
        "context":  {"last_category":"pharmacy","offset":4,"last_cards":[...]}  (ixtiyoriy)
    }
    Javob (web widget bilan aynan bir xil):
    {
        "ok": true, "intent": "nearest_place", "reply": "...",
        "cards": [{title, subtitle, icon, distance, walk, open, phone, url, route_url, lat, lng}],
        "actions": [{label, url} | {label, q}],
        "category": "pharmacy", "next_offset": 4, "source": "local"
    }

Ochiq (autentifikatsiyasiz). DRF sozlamalaridagi standart throttling (anon 60/min)
avtomatik qo'llanadi — server barqarorligi uchun.
"""

from django.http import HttpResponse
from rest_framework.parsers import BaseParser, FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class RawMediaParser(BaseParser):
    """Xom baytlarni (audio/*, octet-stream) o'zgarishsiz oladi.

    DRF standart parserlari audio/webm ni tanimay 415 qaytaradi. Bu parser
    `*/*` ni oladi va oqimni xom baytlar sifatida qaytaradi (STT audiosi uchun).
    Multipart so'rovlar uchun MultiPartParser aniqroq mos kelib, u yutadi.
    """
    media_type = '*/*'

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()

from assistant.service import build_response, parse_location
from assistant import stt as stt_mod, tts as tts_mod


class AssistantChatView(APIView):
    # Ochiq (token SHART EMAS) — lekin token yuborilsa, foydalanuvchi TANIB
    # olinadi. Bu muhim: AI agent faqat tizimga kirgan foydalanuvchi uchun
    # ishlaydi (xarajat himoyasi — assistant/agent.py ga qara). Token bo'lmasa
    # javob avvalgidek keladi, faqat mahalliy dvigatel (engine.py) bilan.
    # Mobil ApiClient har so'rovga Bearer token qo'shadi, shuning uchun Flutter
    # tomonda o'zgartirish kerak emas.
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        message = (data.get('message') or '').strip()
        if not message:
            return Response({'ok': False, 'error': 'empty'}, status=400)
        message = message[:1000]

        location = parse_location(data.get('location'))
        history = data.get('history') if isinstance(data.get('history'), list) else None
        context = data.get('context') if isinstance(data.get('context'), dict) else None
        voice = bool(data.get('voice'))

        # request'ni uzatamiz — tizimga kirgan (tokenli) mobil foydalanuvchi uchun
        # agent to'liq ishlaydi; anonim uchun faqat o'qish tool'lari (places).
        res = build_response(message, location=location, history=history,
                             context=context, request=request, voice=voice)
        return Response(res)


class AssistantTTSView(APIView):
    """`POST /api/assistant/tts/`  {text}  →  audio/mpeg yoki 204 (o'chiq bo'lsa).

    Flutter ilova javob matnini yuboradi, tayyor o'zbek audiosini olib ijro etadi.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        text = (data.get('text') or '').strip()
        if not text:
            return Response({'ok': False, 'error': 'empty'}, status=400)
        audio = tts_mod.synthesize(text)
        if not audio:
            return HttpResponse(status=204)
        resp = HttpResponse(audio, content_type=tts_mod.content_type())
        resp['Cache-Control'] = 'private, max-age=86400'
        return resp


class AssistantSTTView(APIView):
    """`POST /api/assistant/stt/`  (audio)  →  {text} yoki 204 (o'chiq bo'lsa).

    Ochiq (autentifikatsiyasiz) — tts bilan bir xil. Mohir.ai ulangach shu
    endpoint o'zgarmasdan matn qaytara boshlaydi (interfeys — assistant/stt.py).
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, RawMediaParser]

    def post(self, request):
        ctype = request.META.get('CONTENT_TYPE', '')
        f = request.FILES.get('audio')
        if f is not None:
            audio = f.read()
            ctype = f.content_type or ctype
        elif isinstance(request.data, (bytes, bytearray)):
            audio = bytes(request.data)      # RawMediaParser xom baytlar
        else:
            audio = b''
        lang = request.query_params.get('lang') or 'uz'
        text = stt_mod.transcribe(audio, lang=lang, content_type=ctype)
        if not text:
            resp = HttpResponse(status=204)
            resp['X-STT-Available'] = '1' if stt_mod.is_enabled() else '0'
            return resp
        return Response({'ok': True, 'text': text})


class _AssistantActionView(APIView):
    """Tasdiq oqimi uchun umumiy asos — tizimga kirgan foydalanuvchi talab qilinadi.

    Egalik confirm.execute/cancel ichida tekshiriladi (boshqa userniki → 404).
    """
    permission_classes = [IsAuthenticated]
    _fn = None

    def post(self, request, action_id):
        from assistant import confirm
        fn = getattr(confirm, self._fn)
        out = fn(str(action_id), request.user)
        payload = {'ok': out.get('ok', False), 'reply': out.get('reply', '')}
        if out.get('result') is not None:
            payload['result'] = out['result']
        if out.get('pending_id'):
            payload['pending_id'] = out['pending_id']
        status = 200 if out.get('ok') else out.get('status', 400)
        return Response(payload, status=status)


class AssistantConfirmView(_AssistantActionView):
    """`POST /api/assistant/confirm/<uuid>/` — amalni tasdiqlab bajaradi (idempotent)."""
    _fn = 'execute'


class AssistantCancelView(_AssistantActionView):
    """`POST /api/assistant/cancel/<uuid>/` — tasdiq kutayotgan amalni bekor qiladi."""
    _fn = 'cancel'
