"""Ixtiyoriy LLM (katta til modeli) fallback — gibrid rejimning ikkinchi bosqichi.

Mahalliy dvigatel (engine.py) savolni tushunmasa, `views.py` shu modulni chaqiradi.
OpenAI-mos (chat/completions) API bilan ishlaydi — OpenAI, OpenRouter, Groq,
yoki mahalliy server (Ollama, LM Studio) hammasi mos keladi.

SOZLASH (barchasi ixtiyoriy — env orqali):
    AI_API_KEY      — API kalit. BO'SH bo'lsa LLM butunlay o'chadi (xato emas).
    AI_BASE_URL     — endpoint (default: https://api.openai.com/v1)
    AI_MODEL        — model nomi (default: gpt-4o-mini)

Kalit bo'lmasa `ask()` None qaytaradi — sayt bemalol faqat mahalliy dvigatel
bilan ishlayveradi. Bu "gibrid" tanlovning talabi: kalit bo'lmasa faqat mahalliy.
"""

import json
import os
import urllib.request
import urllib.error


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


def is_enabled():
    return bool(os.environ.get('AI_API_KEY', '').strip())


def ask(message, history=None, timeout=20):
    """LLM ga savol yuboradi. Muvaffaqiyatda javob matni (str), aks holda None.

    history — [{role, content}, ...] ko'rinishidagi oldingi xabarlar (ixtiyoriy).
    Har qanday xatolik (kalit yo'q, tarmoq, timeout) — jimgina None qaytaradi,
    shunda chaqiruvchi mahalliy dvigatelning muloyim javobiga qaytadi.
    """
    api_key = os.environ.get('AI_API_KEY', '').strip()
    if not api_key:
        return None

    base_url = os.environ.get('AI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    model = os.environ.get('AI_MODEL', 'gpt-4o-mini').strip()

    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    if history:
        # Faqat oxirgi 6 ta xabarni yuboramiz (token tejash)
        for h in history[-6:]:
            role = h.get('role')
            content = (h.get('content') or '').strip()
            if role in ('user', 'assistant') and content:
                messages.append({'role': role, 'content': content[:2000]})
    messages.append({'role': 'user', 'content': message[:2000]})

    payload = json.dumps({
        'model': model,
        'messages': messages,
        'temperature': 0.3,
        'max_tokens': 500,
    }).encode('utf-8')

    req = urllib.request.Request(
        f'{base_url}/chat/completions',
        data=payload,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return (data['choices'][0]['message']['content'] or '').strip() or None
    except (urllib.error.URLError, KeyError, IndexError, ValueError, TimeoutError):
        return None
