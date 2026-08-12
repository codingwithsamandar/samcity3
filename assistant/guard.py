"""Guard — har bir tool chaqiruvining xavfsizlik darvozasi.

Tartib (registry.dispatch chaqiradi):
  1. Auth      — auth_required tool'ni anonim chaqira olmaydi
  2. Egalik    — order_id/booking_id shu foydalanuvchiniki bo'lishi shart
                 (LLM boshqa ID «to'qib» chiqarsa — denied)
  3. Tuman     — qidiruvlar ctx.district bo'yicha filtrlanadi (apply_district)
  4. Kunlik limit — AgentUsage orqali (suiiste'mol/buzuq tsikl himoyasi)
  5. Audit     — natijadan qat'i nazar AgentAuditLog ga yoziladi

MUHIM: bu modul HECH QACHON istisno tashlamaydi. Rad etish ham xato ham
{ok: False, reply: "..."} lug'ati sifatida qaytadi — foydalanuvchiga o'zbekcha,
tushunarli sabab ko'rsatiladi, chat oqimi buzilmaydi.
"""

import os

from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils import timezone


def _env_int(key, default):
    """Limitni env'dan o'qiydi. Bo'sh/xato bo'lsa — standart (xavfsiz) qiymat.

    Sinov (dev) paytida limitni vaqtincha ko'tarish uchun .env da yuqori qiymat
    beriladi (masalan AI_DAILY_LLM_CALLS=1000000). Ishlab chiqarish (prod) uchun
    env berilmasa — pastdagi xavfsiz standartlar ishlaydi.
    """
    raw = (os.environ.get(key) or '').strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# ── Kunlik limitlar — env orqali sozlanadi, standartlari xavfsiz ─────────────
# Standart qiymatlar prod uchun. Sinov paytida .env da yuqoriroq berib, keyin
# olib tashlash mumkin — kod o'zgarmaydi.
LIMITS = {
    'llm_calls':     _env_int('AI_DAILY_LLM_CALLS', 60),      # kuniga LLM chaqiruvi
    'tool_calls':    _env_int('AI_DAILY_TOOL_CALLS', 200),    # kuniga tool chaqiruvi
    # Taklif (PendingAction yaratish) — arzon, tasdiqlanmasligi mumkin.
    'proposals':     _env_int('AI_DAILY_PROPOSALS', 40),      # kuniga tasdiqqa yuborilgan
    # Haqiqatda BAJARILGAN amal (tasdiqlangan buyurtma/to'lov) — qimmat.
    'mutations':     _env_int('AI_DAILY_MUTATIONS', 20),      # kuniga bajarilgan amal
    'daily_amount':  _env_int('AI_DAILY_AMOUNT', 5_000_000),  # so'm — kunlik jami
    'single_amount': _env_int('AI_SINGLE_AMOUNT', 2_000_000), # so'm — bitta amal
}


def _deny(status, reply, error=''):
    """Standart rad/limit lug'ati (registry natijasi bilan bir xil shakl)."""
    return {'ok': False, 'result_status': status, 'error': error or status,
            'reply': reply, 'speech': reply, 'ui': None, 'silent': False}


# ═══════════════════════════════════════════════════════════════════════════
#  1-4: AVTORIZATSIYA
# ═══════════════════════════════════════════════════════════════════════════

def authorize(spec, params, ctx):
    """Tool bajarilishidan OLDIN tekshiradi. None → ruxsat, aks holda rad lug'ati."""

    # 1) Auth — kirmagan foydalanuvchi auth_required tool'ni chaqira olmaydi.
    if spec.auth_required and not ctx.is_authenticated:
        return _deny('denied',
                     "Buning uchun avval tizimga kiring. 🙂",
                     f"auth kerak: {spec.section}.{spec.action}")

    # 2) Egalik — LLM bergan order_id/booking_id haqiqatan shu userniki bo'lsin.
    own_err = _check_ownership(spec, params, ctx)
    if own_err is not None:
        return own_err

    # 4) Kunlik limit (faqat kirgan foydalanuvchi uchun — AgentUsage user talab qiladi).
    if ctx.is_authenticated:
        limit_err = _check_daily_limits(spec, ctx)
        if limit_err is not None:
            return limit_err

    return None


def _check_ownership(spec, params, ctx):
    """spec.owns = {"order_id": "delivery.Order"} — obyekt ctx.user'niki bo'lsin.

    Ixtiyoriy «:maydon» bilan egalik maydonini ko'rsatish mumkin
    ("delivery.Store:owner"). Standart maydon — 'user'.
    """
    if not spec.owns:
        return None
    for pname, target in spec.owns.items():
        if pname not in params or params[pname] is None:
            continue
        model_path, _, owner_field = target.partition(':')
        owner_field = owner_field or 'user'
        try:
            model = apps.get_model(model_path)
        except (LookupError, ValueError):
            return _deny('error', "Ichki xatolik (model topilmadi).",
                         f"model: {target}")
        if not ctx.is_authenticated:
            return _deny('denied', "Buning uchun avval tizimga kiring. 🙂",
                         "ownership: anonim")
        # ⚠️ Model karta `id` prefiksini («booking:abc») yuborishi mumkin — pk
        # lookup'дан oldin kesamiz. Noto'g'ri pk (UUID emas) → istisno tashlamay,
        # «topilmadi» = denied deб qaraymiz (crash emas).
        pk = params[pname]
        if isinstance(pk, str) and ':' in pk:
            pk = pk.rsplit(':', 1)[-1]
        try:
            obj = model.objects.filter(pk=pk).first()
        except (ValueError, TypeError, ValidationError):
            obj = None
        # Mavjud emas YOKI boshqa odamniki — ikkalasida ham bir xil javob
        # (mavjudligini oshkor qilmaslik uchun).
        if obj is None or getattr(obj, f'{owner_field}_id', None) != ctx.user.id:
            return _deny('denied',
                         "Bu amalni bajarishga ruxsatingiz yo'q.",
                         f"egalik: {target} #{params[pname]}")
    return None


def _check_daily_limits(spec, ctx):
    """AgentUsage bo'yicha kunlik chegaralarni tekshiradi va hisoblagichni oshiradi.

    ⚠️ Mutating tool bu yerda faqat TAKLIF qiladi (PendingAction), hech narsa
    bajarmaydi — shuning uchun `proposals` sanaladi, `mutations` EMAS. Haqiqatda
    bajarilgan amal `confirm.execute()` da `record_mutation()` bilan sanaladi.
    """
    try:
        usage = get_usage(ctx.user)
    except Exception:
        return None  # hisoblagich ishlamasa — bloklamaymiz (server barqarorligi)

    if usage.tool_calls >= LIMITS['tool_calls']:
        return _deny('limited',
                     "Bugungi amal chegarasiga yetdingiz. Ertaga davom ettiramiz. 🙏",
                     'limit: tool_calls')
    if spec.mutating and usage.proposals >= LIMITS['proposals']:
        return _deny('limited',
                     "Bugun juda ko'p amal tasdiqqa yubordingiz. Avval "
                     "tasdiqlanmaganlarini yakunlang yoki ertaga davom ettiramiz. 🙏",
                     'limit: proposals')

    # Chegaradan o'tdi — hisoblagichlarni oshiramiz.
    from django.db.models import F
    fields = {'tool_calls': F('tool_calls') + 1}
    if spec.mutating:
        fields['proposals'] = F('proposals') + 1
    type(usage).objects.filter(pk=usage.pk).update(**fields)
    return None


def check_mutation_limit(user):
    """Tasdiqlangan amal chegarasi. Oshgan bo'lsa rad lug'ati, aks holda None.

    `confirm.execute()` chaqiradi — ya'ni tekshiruv amal HAQIQATDA bajarilishidan
    oldin bo'ladi (taklif paytida emas).
    """
    try:
        if user is None or not getattr(user, 'is_authenticated', False):
            return None
        usage = get_usage(user)
    except Exception:
        return None
    if usage.mutations >= LIMITS['mutations']:
        return _deny('limited',
                     "Bugun juda ko'p buyurtma/amal bajardingiz. Xavfsizlik uchun "
                     "ertagacha to'xtatdim. 🙏",
                     'limit: mutations')
    return None


def record_mutation(user):
    """Tasdiqlanib BAJARILGAN amalni sanaydi (confirm.execute muvaffaqiyatida)."""
    try:
        if user is None or not getattr(user, 'is_authenticated', False):
            return
        usage = get_usage(user)
        from django.db.models import F
        type(usage).objects.filter(pk=usage.pk).update(mutations=F('mutations') + 1)
    except Exception:
        pass


def check_amount(ctx, amount):
    """Summa limitlari (bitta amal + kunlik jami). None → ruxsat, aks holda limit."""
    try:
        amount = int(amount or 0)
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0:
        return None
    if amount > LIMITS['single_amount']:
        return _deny('limited',
                     f"Bu amal summasi ({_som(amount)}) bitta amal chegarasidan "
                     f"({_som(LIMITS['single_amount'])}) oshib ketdi. Kattaroq "
                     "to'lovni saytdan qo'lda bajaring. 🙏",
                     'limit: single_amount')
    if ctx.is_authenticated:
        try:
            usage = get_usage(ctx.user)
            if int(usage.total_amount) + amount > LIMITS['daily_amount']:
                return _deny('limited',
                             "Bugungi umumiy to'lov chegarasiga yetdingiz. "
                             "Ertaga davom ettiramiz. 🙏",
                             'limit: daily_amount')
        except Exception:
            return None
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  3: TUMAN FILTRI
# ═══════════════════════════════════════════════════════════════════════════

def apply_district(qs, ctx, path='neighborhood__district'):
    """QuerySet'ni ctx.district bo'yicha filtrlaydi.

    ⚠️ Bu filtr LLM'dan EMAS, ctx (server)dan keladi — AI uni ko'rmaydi ham,
    o'zgartira olmaydi ham. district bo'lmasa (anonim yoki mahalla tanlanmagan)
    — filtr qo'llanmaydi (butun shahar ko'rinadi).
    """
    if ctx is None or ctx.district is None:
        return qs
    try:
        return qs.filter(**{path: ctx.district})
    except Exception:
        return qs


# ═══════════════════════════════════════════════════════════════════════════
#  5: AUDIT + hisoblagichlar
# ═══════════════════════════════════════════════════════════════════════════

def get_usage(user):
    """Bugungi AgentUsage yozuvi (bo'lmasa yaratadi). Faqat kirgan user uchun."""
    from .models import AgentUsage
    usage, _ = AgentUsage.objects.get_or_create(
        user=user, date=timezone.localdate())
    return usage


def record_llm_call(ctx, tokens_in=0, tokens_out=0):
    """LLM chaqiruvini hisoblagichga qo'shadi. Limitdan oshgan bo'lsa True (bloklandi)."""
    if not ctx.is_authenticated:
        # Anonim foydalanuvchi bu yergacha YETIB KELMASLIGI kerak: `agent.run()`
        # kirmagan odamni boshidayoq to'sadi (xarajat kafolati). Bu shart —
        # ikkinchi qavat himoya: agar kelajakda kimdir agentni boshqa joydan
        # chaqirsa, anonimda hisoblagich yo'qligi sababli limit ishlamaydi,
        # shuning uchun bu yerda ham hech narsa sanamaymiz.
        return False
    try:
        usage = get_usage(ctx.user)
        if usage.llm_calls >= LIMITS['llm_calls']:
            return True
        from django.db.models import F
        type(usage).objects.filter(pk=usage.pk).update(llm_calls=F('llm_calls') + 1)
    except Exception:
        return False
    return False


def record_amount(user, amount):
    """Tasdiqlangan amal summasini kunlik jamiga qo'shadi (confirm.execute chaqiradi)."""
    try:
        amount = int(amount or 0)
        if amount <= 0 or user is None or not getattr(user, 'is_authenticated', False):
            return
        usage = get_usage(user)
        from django.db.models import F
        type(usage).objects.filter(pk=usage.pk).update(
            total_amount=F('total_amount') + amount)
    except Exception:
        pass


def audit(ctx, section, action, params, result, duration_ms=0):
    """Har bir chaqiruvni AgentAuditLog ga yozadi. HECH QACHON istisno tashlamaydi."""
    try:
        from .models import AgentAuditLog
        status = (result or {}).get('result_status', 'ok')
        if status not in dict(AgentAuditLog.RESULT_CHOICES):
            status = 'ok' if (result or {}).get('ok', True) else 'error'
        user = ctx.user if (ctx and ctx.is_authenticated) else None
        AgentAuditLog.objects.create(
            user=user,
            session_key=(ctx.session_key if ctx else '') or '',
            task_id=(getattr(ctx.task, 'id', None) if ctx and ctx.task else None),
            section=section[:24], action=action[:40],
            params=_safe_json(params),
            result_status=status,
            error=str((result or {}).get('error', ''))[:300],
            duration_ms=max(0, int(duration_ms or 0)),
        )
    except Exception:
        pass


def _safe_json(params):
    """Audit uchun parametrlarni xavfsiz JSON'ga keltiradi (seriyalanmasa — str)."""
    try:
        import json
        json.dumps(params)
        return params
    except (TypeError, ValueError):
        return {'_repr': str(params)[:500]}


def _som(v):
    try:
        return f"{int(v):,}".replace(',', ' ') + " so'm"
    except (TypeError, ValueError):
        return str(v)
