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
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from assistant.service import build_response, parse_location
from assistant import tts as tts_mod


class AssistantChatView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # ochiq ma'lumot — mobil ilovada token shart emas

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        message = (data.get('message') or '').strip()
        if not message:
            return Response({'ok': False, 'error': 'empty'}, status=400)
        message = message[:1000]

        location = parse_location(data.get('location'))
        history = data.get('history') if isinstance(data.get('history'), list) else None
        context = data.get('context') if isinstance(data.get('context'), dict) else None

        res = build_response(message, location=location, history=history, context=context)
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
        resp = HttpResponse(audio, content_type='audio/mpeg')
        resp['Cache-Control'] = 'private, max-age=86400'
        return resp
