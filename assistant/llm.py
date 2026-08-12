"""LLM adapteri — tool-calling, oqim (streaming) va provayderlar.

Uch qatlamli oqimning ikkinchi bosqichi. `engine.py` savolni tushunmasa,
`agent.py` shu moduldan foydalanib LLM bilan tool halqasini yuritadi.

Provayderlar (AI_PROVIDER):
  openai      — OpenAI Chat Completions (tool_calls, argumentlar JSON satr)
  openrouter  — OpenAI-mos (faqat boshqa base_url/model)
  gemini      — Google Generative Language (functionCall/functionResponse)

SOZLASH (env — barchasi ixtiyoriy):
  AI_PROVIDER=openai            # openai | openrouter | gemini
  AI_API_KEY=...                # BO'SH bo'lsa LLM butunlay o'chadi (xato emas)
  AI_BASE_URL=...               # standart provayderga qarab
  AI_MODEL=gpt-4o-mini
  AI_AGENT_ENABLED=1            # 0 → agent o'chadi, faqat engine.py ishlaydi

⚠️ Kalit bo'lmasa yoki xato bo'lsa — HECH QACHON istisno tashlanmaydi. `call()`
None, `ask()` None qaytaradi va sayt bemalol faqat `engine.py` bilan ishlayveradi.
Bu «muloyim degradatsiya» — mavjud xatti-harakat, buzmaymiz.
"""

import json
import os
import re
import urllib.error
import urllib.request


# Eski, oddiy savol-javob uchun (orqaga moslik — service.py hali ham chaqiradi).
SYSTEM_PROMPT = (
    "Sen SamCity super-ilovasining yordamchisisan. SamCity — O'zbekistondagi "
    "Shofirkon shahri uchun raqamli platforma: e'lonlar (oldi-sotdi), taksi, "
    "do'konlar va yetkazib berish, xarita/joylar (dorixona, shifoxona, bank, "
    "restoran va h.k.), to'yxona bron qilish, ish e'lonlari, mahalla xizmatlari. "
    "Foydalanuvchiga qisqa, do'stona va foydali javob ber. Asosan o'zbek tilida "
    "javob ber (agar savol rus yoki ingliz tilida bo'lsa — o'sha tilda). "
    "Aniq manzil yoki joyni bilmasang, foydalanuvchiga xarita bo'limidan "
    "qidirishni maslahat ber. Uydirma ma'lumot (masalan aniq telefon raqami) "
    "berma."
)

_DEFAULT_BASE = {
    'openai': 'https://api.openai.com/v1',
    'openrouter': 'https://openrouter.ai/api/v1',
    'gemini': 'https://generativelanguage.googleapis.com/v1beta',
}


# ── Sozlama yordamchilari ────────────────────────────────────────────────────

def _provider():
    return os.environ.get('AI_PROVIDER', 'openai').strip().lower() or 'openai'


def _api_key():
    return os.environ.get('AI_API_KEY', '').strip()


def _base_url():
    prov = _provider()
    return os.environ.get('AI_BASE_URL', _DEFAULT_BASE.get(prov, _DEFAULT_BASE['openai'])).rstrip('/')


def _model():
    return os.environ.get('AI_MODEL', 'gpt-4o-mini').strip()


def is_enabled():
    """LLM (oddiy javob) yoqilganmi — kalit bor bo'lsa."""
    return bool(_api_key())


def agent_enabled():
    """Tool-calling agent yoqilganmi — kalit bor VA AI_AGENT_ENABLED != 0."""
    if not _api_key():
        return False
    return os.environ.get('AI_AGENT_ENABLED', '1').strip() not in ('0', 'false', 'no', '')


# ═══════════════════════════════════════════════════════════════════════════
#  ESKI ASK() — o'zgarmagan (orqaga moslik)
# ═══════════════════════════════════════════════════════════════════════════

def ask(message, history=None, timeout=20):
    """Oddiy LLM javobi (tool'siz). Muvaffaqiyatda matn (str), aks holda None."""
    if not _api_key():
        return None
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    if history:
        for h in history[-6:]:
            role = h.get('role')
            content = (h.get('content') or '').strip()
            if role in ('user', 'assistant') and content:
                messages.append({'role': role, 'content': content[:2000]})
    messages.append({'role': 'user', 'content': message[:2000]})
    res = call(messages, timeout=timeout, max_tokens=500)
    if not res:
        return None
    return (res.get('content') or '').strip() or None


# ═══════════════════════════════════════════════════════════════════════════
#  CALL() — tool-calling (oqimsiz). agent.py shuni ishlatadi.
# ═══════════════════════════════════════════════════════════════════════════

def call(messages, tools=None, max_tokens=500, temperature=0.3, timeout=25):
    """LLM ga so'rov yuboradi. Qaytaradi: {content, tool_calls, usage} yoki None.

    tool_calls — normallashgan: [{"id","name","arguments": dict}]. `name` — bo'lim
    (section). `arguments` ichida `action` va qolgan parametrlar bo'ladi.
    Har qanday xato → None (chat oqimi buzilmasin).
    """
    if not _api_key():
        return None
    _LAST_ERROR['value'] = None
    try:
        if _provider() == 'gemini':
            return _call_gemini(messages, tools, max_tokens, temperature, timeout)
        return _call_openai(messages, tools, max_tokens, temperature, timeout)
    except urllib.error.HTTPError as e:
        # ⚠️ Xato JIMGINA yutilsa diagnostika imkonsiz bo'ladi: 429 (tezlik
        # limiti) yoki 403 (Cloudflare) bo'lsa ham javob shunchaki bo'sh
        # ko'rinardi. Xatti-harakat o'zgarmaydi (None qaytadi — muloyim
        # degradatsiya), lekin endi sabab jurnalga ham, `last_error()` ga ham
        # yoziladi.
        try:
            body = e.read().decode('utf-8', errors='replace')[:400]
        except Exception:
            body = ''
        return _fail(f'HTTP {e.code} {e.reason}: {body}')
    except (urllib.error.URLError, TimeoutError) as e:
        return _fail(f'tarmoq: {getattr(e, "reason", e)}')
    except (KeyError, IndexError, ValueError, TypeError) as e:
        return _fail(f'javobni o\'qib bo\'lmadi: {type(e).__name__}: {e}')


# Oxirgi xato sababi — diagnostika uchun (smoke_agent, debug_llm o'qiydi).
_LAST_ERROR = {'value': None}


def last_error():
    """Oxirgi muvaffaqiyatsiz `call()` sababi (yoki None)."""
    return _LAST_ERROR['value']


def _fail(reason):
    import logging
    _LAST_ERROR['value'] = reason
    logging.getLogger('assistant').warning('LLM so\'rovi muvaffaqiyatsiz — %s', reason)
    return None


# ⚠️ User-Agent MAJBURIY. Cloudflare orqasidagi provayderlar (Groq, OpenRouter
# va boshqalar) `urllib` ning standart "Python-urllib/3.x" imzosini bot deb
# biladi va so'rovni API'gacha yetkazmasdan rad etadi (HTTP 403, xato 1010).
# Empirik tekshirildi: standart UA → 403, istalgan boshqa UA → 200.
# Env orqali o'zgartirish mumkin (AI_USER_AGENT).
_DEFAULT_UA = 'SamCity/1.0 (+https://samcity.uz)'


def _user_agent():
    return os.environ.get('AI_USER_AGENT', '').strip() or _DEFAULT_UA


def _http_json(url, payload, headers, timeout):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json',
                 'User-Agent': _user_agent(), **headers}, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _call_openai(messages, tools, max_tokens, temperature, timeout):
    payload = {
        'model': _model(), 'messages': messages,
        'temperature': temperature, 'max_tokens': max_tokens,
    }
    if tools:
        payload['tools'] = tools
        payload['tool_choice'] = 'auto'
    data = _http_json(f'{_base_url()}/chat/completions', payload,
                      {'Authorization': f'Bearer {_api_key()}'}, timeout)
    msg = data['choices'][0]['message']
    tool_calls = []
    for tc in (msg.get('tool_calls') or []):
        fn = tc.get('function', {})
        tool_calls.append({
            'id': tc.get('id', ''),
            'name': fn.get('name', ''),
            'arguments': _parse_args(fn.get('arguments', '')),
        })
    return {
        'content': (msg.get('content') or ''),
        'tool_calls': tool_calls,
        'usage': data.get('usage', {}),
    }


def _call_gemini(messages, tools, max_tokens, temperature, timeout):
    """Gemini adapteri — OpenAI xabarlarini Gemini sxemasiga aylantiradi."""
    system_txt, contents = _to_gemini_contents(messages)
    payload = {
        'contents': contents,
        'generationConfig': {'temperature': temperature, 'maxOutputTokens': max_tokens},
    }
    if system_txt:
        payload['systemInstruction'] = {'parts': [{'text': system_txt}]}
    if tools:
        payload['tools'] = [{'functionDeclarations': _to_gemini_tools(tools)}]

    url = f'{_base_url()}/models/{_model()}:generateContent?key={_api_key()}'
    data = _http_json(url, payload, {}, timeout)
    cand = (data.get('candidates') or [{}])[0]
    parts = (cand.get('content') or {}).get('parts', []) or []
    content, tool_calls = '', []
    for p in parts:
        if 'text' in p:
            content += p['text']
        elif 'functionCall' in p:
            fc = p['functionCall']
            tool_calls.append({
                'id': '', 'name': fc.get('name', ''),
                'arguments': fc.get('args', {}) or {},
            })
    return {'content': content, 'tool_calls': tool_calls,
            'usage': data.get('usageMetadata', {})}


def _to_gemini_contents(messages):
    """OpenAI [{role,content}] → (system_text, gemini_contents). system birlashtiriladi."""
    system_parts, contents = [], []
    for m in messages:
        role = m.get('role')
        text = m.get('content') or ''
        if role == 'system':
            system_parts.append(text)
        elif role in ('user', 'assistant'):
            contents.append({'role': 'model' if role == 'assistant' else 'user',
                             'parts': [{'text': text}]})
    return "\n\n".join(system_parts), contents


def _to_gemini_tools(openai_tools):
    """OpenAI `tools` → Gemini `functionDeclarations`."""
    decls = []
    for t in openai_tools:
        fn = t.get('function', {})
        decls.append({
            'name': fn.get('name'),
            'description': fn.get('description', '')[:1000],
            'parameters': fn.get('parameters', {'type': 'object', 'properties': {}}),
        })
    return decls


def _parse_args(raw):
    """Tool argumentlarini dict ga aylantiradi. Xato bo'lsa — bo'sh dict (xavfsiz)."""
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        val = json.loads(raw)
        return val if isinstance(val, dict) else {}
    except (ValueError, TypeError):
        return {}


# ═══════════════════════════════════════════════════════════════════════════
#  OQIMLI TOOL-CALL FRAGMENTLARINI YIG'ISH (tuzoq — 4.3)
# ═══════════════════════════════════════════════════════════════════════════

def assemble_tool_calls(chunks):
    """Oqimdagi tool_call bo'laklarini `index` bo'yicha yig'adi.

    Oqim rejimida `function.name` va `function.arguments` bo'lak-bo'lak keladi.
    Ularni MATN SIFATIDA ulaymiz (har bo'lakni alohida parse qilish — XATO),
    oxirida bir marta json.loads. Parse muvaffaqiyatsiz bo'lsa xom satr qoladi
    (tool bajaruvchisi hal qiladi — bo'sh dict).

    chunks — [{index, id?, function:{name?, arguments?}}, ...] (delta bo'laklari).
    """
    acc = {}
    for ch in chunks:
        idx = ch.get('index', 0)
        slot = acc.setdefault(idx, {'id': '', 'name': '', 'arguments': ''})
        if ch.get('id'):
            slot['id'] = ch['id']
        fn = ch.get('function') or {}
        if fn.get('name'):
            slot['name'] += fn['name']
        if fn.get('arguments'):
            slot['arguments'] += fn['arguments']  # ← matn sifatida ulanadi

    result = []
    for idx in sorted(acc):
        slot = acc[idx]
        result.append({'id': slot['id'], 'name': slot['name'],
                       'arguments': _parse_args(slot['arguments'])})
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  O'ZBEKCHA JUMLA AJRATISH (oqimli TTS uchun — 4.4)
# ═══════════════════════════════════════════════════════════════════════════

# Jumla oxiri: .!?… + probel yoki matn oxiri. Probelsiz nuqta (8.5, t.me) — jumla EMAS.
_SENT_END = re.compile(r'([.!?…]+)(\s+|$)')
# Nuqta bilan tugaydigan qisqartmalar — bulardan keyin jumla bo'linmaydi.
_ABBREVS = ('va h.k', 'h.k', 'v.b', 'sh.k', 'va b', 'т.д', 'т.п')


def split_sentences(text):
    """Matnni jumlalarga bo'ladi. O'zbekcha tuzoqlarni istisno qiladi:

    «35 000 so'm» (probelli son) · «8.5 km» (o'nlik) · «soat 14.30» (vaqt) ·
    «va h.k.» (qisqartma) · «1-chi» (tartib son) · «t.me/samcity» (havola).
    """
    text = text or ''
    out, start = [], 0
    for m in _SENT_END.finditer(text):
        seg = text[start:m.end()].strip()
        if not seg:
            start = m.end()
            continue
        # Qisqartma bilan tugasa (h.k. va b.) — jumla chegarasi emas.
        low = seg.lower().rstrip('.').rstrip()
        if any(low.endswith(ab) for ab in _ABBREVS):
            continue
        out.append(seg)
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


class SentenceStreamer:
    """Oqimli matnni to'liq jumlalar chiqqan sari beradi — TTS ni erta boshlash uchun.

    `feed(chunk)` → tayyor jumlalar ro'yxati (oxirgi, tugallanmagan qism buferda
    qoladi). `flush()` → qolgan matn.
    """

    def __init__(self):
        self._buf = ''

    def feed(self, chunk):
        self._buf += (chunk or '')
        sents = split_sentences(self._buf)
        if len(sents) <= 1:
            return []
        # Oxirgisi tugallanmagan bo'lishi mumkin — uni buferda qoldiramiz.
        *ready, last = sents
        self._buf = last
        return ready

    def flush(self):
        rest = self._buf.strip()
        self._buf = ''
        return [rest] if rest else []


def iter_sentences(text):
    """Tayyor matnni jumlalar bo'yicha beradi (oddiy generator)."""
    for s in split_sentences(text):
        yield {'type': 'sentence', 'text': s}
