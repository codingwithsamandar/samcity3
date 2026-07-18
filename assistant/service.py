"""AI yordamchi — umumiy javob mantigʻi (web widget + mobil API bir xil ishlatadi).

Web view (assistant/views.py) va mobil REST API (api/assistant_views.py) — ikkalasi
ham shu `build_response()` ni chaqiradi. Shu tufayli xatti-harakat aynan bir xil:
mahalliy dvigatel → tushunmasa jurnal + LLM (sozlangan boʻlsa) → foydali fallback.
"""

from . import engine, llm


def build_response(message, location=None, history=None, context=None):
    """Asistant javobini (dict) qaytaradi — kanal (web/mobil)dan qatʼi nazar bir xil."""
    res = engine.handle(message, location=location, context=context)

    if res.get('intent') == 'unknown':
        # Tushunilmagan savolni jurnalga yozamiz (KB'ni kengaytirish uchun)
        try:
            from . import models as amodels
            amodels.record_unanswered(message)
        except Exception:
            pass
        answer = llm.ask(message, history=history)
        if answer:
            res['reply'] = answer
            res['intent'] = 'llm'
            res['source'] = 'llm'
        else:
            fb = engine.fallback(message)
            res['reply'] = fb['reply']
            res['actions'] = fb.get('actions', [])
            res['intent'] = 'fallback'
            res['source'] = 'local'
    else:
        res['source'] = 'local'

    res['ok'] = True
    return res


def parse_location(raw):
    """{'lat':.., 'lng':..} → (lat, lng) yoki None. Web va API uchun umumiy."""
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
