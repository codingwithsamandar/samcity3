"""AI yordamchi — umumiy javob mantigʻi (web widget + mobil API bir xil ishlatadi).

Web view (assistant/views.py) va mobil REST API (api/assistant_views.py) — ikkalasi
ham shu `build_response()` ni chaqiradi. Shu tufayli xatti-harakat aynan bir xil.

Uch qatlamli oqim (JARVIS_REJA — arxitektura qarori):
  1) engine.handle()  — mahalliy dvigatel (5ms, 0 so'm). ~45% so'rov shu yerda hal.
  2) agent.run()      — tool-calling agent (LLM + tool halqasi), request bo'lsa.
  3) llm.ask()        — oddiy LLM javobi (agent o'chiq bo'lsa, orqaga moslik).
  4) engine.fallback()— hech biri ishlamasa — foydali yo'naltiruvchi javob.

`request` berilsa agent ishga tushadi (ctx — kim/qayerdan serverdan keladi).
Berilmasa (eski chaqiruvlar) — avvalgidek engine + llm.ask.
"""

from . import engine, llm

# Engine shu intent'larni qaytarса, agent (kirgan foydalanuvchi uchun) TO'LIQROQ
# hal qiladi — engine chekinadi. `places`/`popular`/`faq`/`greeting`/`help`/
# `smalltalk` engine'да qoladi (bepul, agent shart emas).
_AGENT_OWNED_INTENTS = {'delivery', 'ads', 'jobs', 'booking', 'taxi'}


def build_response(message, location=None, history=None, context=None,
                   request=None, voice=False):
    """Asistant javobini (dict) qaytaradi — kanal (web/mobil)dan qatʼi nazar bir xil."""

    # ── FAOL VAZIFA → AGENT EGALLAYDI (engine'ni chetlab o'tamiz) ─────────────
    # Yarim qolgan bron/buyurtma vazifasi bor bo'lsa, suhbatni agent boshqaradi.
    # Aks holда «soch olish», «11 da», «ha» kabi qisqa javoblarni engine mustaqil
    # so'rov deб talqin qilib (soch→barber toifasi), oqimni UZADI (PROMPT_10).
    # Faqat kirgan foydalanuvchi; agent None qaytarsa engine'ga tushib davom
    # etamiz (zaxira). Vazifa tugagach (status != active) — keyingi xabar yana
    # engine fast-path'iga tushadi (oddiy so'rovlar bepul qoladi).
    if request is not None and not _is_anonymous(request) and _has_active_task(request):
        agent_res = _try_agent(message, history, location, request, voice)
        if agent_res is not None:
            return _as_agent_response(agent_res)

    res = engine.handle(message, location=location, context=context)

    if res.get('intent') != 'unknown':
        # ── AGENT EGALLAGAN BO'LIMLAR → engine chekinsin ─────────────────────
        # Engine'да delivery/ads/jobs/booking/taxi bo'yicha ESKI branch'lar bor
        # (havola/oddiy javob). Agentда bu bo'limlar TO'LIQ (savat, e'lon joylash,
        # bron, taksi chaqirish). Kirgan foydalanuvchi uchun agentга beramiz —
        # aks holда «e'lonlarni qidir», «savatimда nima bor» engine'ga tushib,
        # agentни soya qiladi. Agent None qaytarsa (LLM o'chiq/ishlamadi) engine
        # natijasига qaytamiz (no-key zaxira — kartalar yo'qolmaydi).
        if (request is not None and not _is_anonymous(request)
                and (res.get('intent') in _AGENT_OWNED_INTENTS
                     or engine.is_community_query(message)
                     or engine.is_account_query(message))):
            agent_res = _try_agent(message, history, location, request, voice)
            if agent_res is not None:
                return _as_agent_response(agent_res)
        res['source'] = 'local'
        res['ok'] = True
        return res

    # ── Tushunilmagan savol: jurnalga yozamiz (KB'ni kengaytirish uchun) ──────
    try:
        from . import models as amodels
        amodels.record_unanswered(message)
    except Exception:
        pass

    # ── ANONIM FOYDALANUVCHI: LLM ga umuman bormaydi (xarajat kafolati) ───────
    # Chat endpoint'i ochiq. Kirmagan odam uchun na agent, na oddiy llm.ask
    # chaqiriladi — aks holda tarqatilgan IP'lardan cheksiz LLM sarfi mumkin.
    # U engine.py bilan to'liq ishlaydi, faqat tushunilmagan savolda muloyim
    # taklif ko'radi. `request` berilmagan (eski chaqiruv) bo'lsa — kimligini
    # bilmaymiz, avvalgi xatti-harakat saqlanadi.
    if _is_anonymous(request):
        return _anon_fallback(res, message)

    # ── 2-bosqich: tool-calling agent (request bo'lsa) ────────────────────────
    agent_res = _try_agent(message, history, location, request, voice)
    if agent_res is not None:
        return _as_agent_response(agent_res)

    # ── 3-bosqich: oddiy LLM javobi (agent o'chiq/ishlamadi) ──────────────────
    answer = llm.ask(message, history=history)
    if answer:
        res['reply'] = answer
        res['intent'] = 'llm'
        res['source'] = 'llm'
        res['ok'] = True
        return res

    # ── 4-bosqich: muloyim fallback ───────────────────────────────────────────
    fb = engine.fallback(message)
    res['reply'] = fb['reply']
    res['actions'] = fb.get('actions', [])
    res['intent'] = 'fallback'
    res['source'] = 'local'
    res['ok'] = True
    return res


def _is_anonymous(request):
    """Kimligi ANIQ ma'lum va kirmagan bo'lsa True. request yo'q bo'lsa False."""
    if request is None:
        return False
    user = getattr(request, 'user', None)
    return not bool(user is not None and getattr(user, 'is_authenticated', False))


def _has_active_task(request):
    """Shu foydalanuvchi uchun yarim qolgan (active, muddati o'tmagan) vazifa bormi.

    `task.active_task()` mantiqини qayta ishlatadi (dublikat emas) — u muddati
    o'tganini `abandoned` qiladi va user/session bo'yicha filtrlaydi. Bitta
    indekslangan so'rov — arzon.
    """
    try:
        from . import registry, task as task_mod
        ctx = registry.build_context(request)
        return task_mod.active_task(ctx) is not None
    except Exception:
        return False


def _as_agent_response(agent_res):
    """Agent natijasidan to'liq javob lug'atini quradi (yangi va eski yo'l bir xil).

    Widget kutadigan kalitlar: reply, ui, cards, actions, pending_id, silent.
    """
    out = {
        'ok': True, 'intent': 'agent', 'source': 'agent',
        'reply': agent_res.get('reply', ''), 'cards': [], 'actions': [],
    }
    for key in ('ui', 'pending_id'):
        if agent_res.get(key) is not None:
            out[key] = agent_res[key]
    if agent_res.get('silent'):
        out['silent'] = True
    return out


def _anon_fallback(res, message):
    """Anonim foydalanuvchi uchun fallback + «tizimga kirsangiz» taklifi.

    `engine.py` ga tegilmaydi (u kim so'rayotganini bilmaydi) — qo'shimcha shu
    yerda, javob tuzilayotganda qo'shiladi.
    """
    # ⚠️ Harakat niyati (bron/buyurtma) bo'lsa — engine chekingan, agent esa
    # anonimда o'chiq. Muloyim ravishда «kiring» deymiz (jimgina manzil emas).
    if engine.is_action_intent(message):
        res['reply'] = ("Bron va buyurtma qilish uchun avval tizimga kiring — "
                        "keyin men to'g'ridan-to'g'ri joy tanlab, bron/buyurtma "
                        "qilib beraman. 🔐")
        res['intent'] = 'fallback'
        res['source'] = 'local'
        res['ok'] = True
        try:
            from django.urls import reverse
            res['actions'] = [{'label': '🔐 Kirish / Ro‘yxatdan o‘tish',
                               'url': reverse('login')}]
        except Exception:
            res['actions'] = []
        return res

    fb = engine.fallback(message)
    res['reply'] = fb['reply'] + (
        "\n\n🔐 Aytgancha: tizimga kirsangiz, AI yordamchi ancha ko'proq ish "
        "qila oladi — do'kondan buyurtma berish, savat to'ldirish va boshqalar."
    )
    actions = list(fb.get('actions', []))
    try:
        from django.urls import reverse
        actions.insert(0, {'label': '🔐 Kirish / Ro‘yxatdan o‘tish',
                           'url': reverse('login')})
    except Exception:
        pass
    res['actions'] = actions
    res['intent'] = 'fallback'
    res['source'] = 'local'
    res['ok'] = True
    return res


def _try_agent(message, history, location, request, voice):
    """Agentni ishga tushiradi (request bo'lsa). Hech qachon istisno tashlamaydi."""
    if request is None:
        return None
    try:
        from . import agent, registry, task as task_mod
        ctx = registry.build_context(request, location=location, voice=voice)
        # Faol (yarim qolgan) vazifani kontekstga bog'laymiz — davom ettirish uchun.
        try:
            ctx.task = task_mod.active_task(ctx)
        except Exception:
            ctx.task = None
        return agent.run(message, ctx, history=history)
    except Exception:
        return None


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
