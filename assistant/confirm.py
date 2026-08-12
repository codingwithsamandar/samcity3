"""Tasdiqlash oqimi — PendingAction yaratish va (tasdiqdan keyin) bajarish.

Butun xavfsizlik modelining yuragi: LLM `create_pending()` orqali «nima
qilinishi kerak»ligini yozib qo'yadi, lekin bajarish faqat foydalanuvchi
tasdiq tugmasini bosgach, `execute()` orqali bo'ladi.

`execute()` — IDEMPOTENT: tugma ikki marta bosilsa ham bitta buyurtma yaratiladi
(qator `select_for_update()` bilan qulflanadi, holat tekshiriladi).
"""

from django.db import transaction
from django.utils import timezone

from . import registry


def create_pending(ctx, section, action, payload, summary_card=None, amount=0):
    """Tasdiq kutayotgan amal yozadi. Hech narsa bajarilmaydi.

    Faqat kirgan foydalanuvchi uchun (PendingAction.user majburiy). Anonim bo'lsa
    None qaytaradi — chaqiruvchi (registry) buni xatoga aylantiradi.
    """
    if ctx is None or not ctx.is_authenticated:
        return None
    from .models import PendingAction
    try:
        return PendingAction.objects.create(
            user=ctx.user,
            task=(ctx.task if ctx.task else None),
            section=section[:24], action=action[:40],
            payload=payload or {},
            summary_card=summary_card or {},
            amount=amount or 0,
        )
    except Exception:
        return None


def execute(action_id, user):
    """Tasdiqlangan amalni bajaradi — IDEMPOTENT.

    Qaytaradi: {ok, status, reply, result, ...}. `status` — HTTP maslahati:
      404 — topilmadi YOKI boshqa userniki (mavjudligini oshkor qilmaymiz)
      200 — bajarildi yoki allaqachon bajarilgan (idempotent)
      410 — muddati o'tgan
      409 — bekor qilingan
    """
    from .models import PendingAction

    with transaction.atomic():
        pa = (PendingAction.objects
              .select_for_update()
              .filter(id=action_id, user=user)
              .first())
        if pa is None:
            return {'ok': False, 'status': 404, 'error': 'not_found',
                    'reply': "Bunday amal topilmadi."}

        # Idempotentlik: allaqachon yakunlangan bo'lsa — qayta bajarmaymiz.
        if pa.status == 'confirmed':
            return {'ok': True, 'status': 200, 'idempotent': True,
                    'reply': _success_reply(pa), 'result': pa.result,
                    'pending_id': str(pa.id)}
        if pa.status == 'cancelled':
            return {'ok': False, 'status': 409, 'error': 'cancelled',
                    'reply': "Bu amal bekor qilingan."}
        if pa.status in ('expired', 'failed'):
            return {'ok': False, 'status': 410, 'error': pa.status,
                    'reply': pa.result.get('error') or "Bu amalning muddati o'tgan.",
                    'result': pa.result}

        # Muddati o'tganmi?
        if pa.is_expired:
            pa.status = 'expired'
            pa.save(update_fields=['status'])
            return {'ok': False, 'status': 410, 'error': 'expired',
                    'reply': "Amalning muddati o'tib ketdi. Iltimos, qaytadan boshlang."}

        # Kunlik BAJARILGAN amal chegarasi — aynan shu yerda tekshiriladi
        # (taklif paytida emas). Yozuv 'pending' bo'lib qoladi: limit tiklangach
        # (ertaga) yoki muddati o'tguncha foydalanuvchi qayta urinishi mumkin.
        from . import guard as _guard
        limit_err = _guard.check_mutation_limit(user)
        if limit_err is not None:
            return {'ok': False, 'status': 429, 'error': 'limit_mutations',
                    'reply': limit_err['reply']}

        # Bajaruvchini topamiz (LLM ga ko'rinmaydigan @executor).
        fn = registry.get_executor(pa.section, pa.action)
        if fn is None:
            pa.status = 'failed'
            pa.result = {'error': f"executor yo'q: {pa.section}.{pa.action}"}
            pa.save(update_fields=['status', 'result'])
            return {'ok': False, 'status': 500, 'error': 'no_executor',
                    'reply': "Ichki xatolik: amalni bajaruvchi topilmadi."}

        try:
            result = fn(pa.payload, user) or {}
        except Exception as e:  # noqa: BLE001
            pa.status = 'failed'
            pa.result = {'error': f"{type(e).__name__}: {e}"[:500]}
            pa.save(update_fields=['status', 'result'])
            return {'ok': False, 'status': 500, 'error': 'exec_failed',
                    'reply': "Amalni bajarishda xatolik yuz berdi.",
                    'result': pa.result}

        pa.status = 'confirmed'
        pa.confirmed_at = timezone.now()
        pa.result = result
        pa.save(update_fields=['status', 'confirmed_at', 'result'])

    # Tranzaksiyadan tashqarida — hisoblagichlar (limitga ta'sir qiladi, xatoga
    # chidamli). Amal HAQIQATDA bajarildi, shuning uchun `mutations` shu yerda
    # sanaladi (taklif paytida emas — `proposals` alohida).
    from . import guard
    guard.record_mutation(user)
    guard.record_amount(user, pa.amount)

    return {'ok': True, 'status': 200, 'reply': _success_reply(pa),
            'result': result, 'pending_id': str(pa.id)}


def cancel(action_id, user):
    """Tasdiq kutayotgan amalni bekor qiladi. Egalik: boshqa userniki → 404."""
    from .models import PendingAction
    with transaction.atomic():
        pa = (PendingAction.objects
              .select_for_update()
              .filter(id=action_id, user=user)
              .first())
        if pa is None:
            return {'ok': False, 'status': 404, 'error': 'not_found',
                    'reply': "Bunday amal topilmadi."}
        if pa.status == 'cancelled':
            return {'ok': True, 'status': 200, 'idempotent': True,
                    'reply': "Amal bekor qilingan."}
        if pa.status != 'pending':
            return {'ok': False, 'status': 409, 'error': pa.status,
                    'reply': "Bu amalni endi bekor qilib bo'lmaydi."}
        pa.status = 'cancelled'
        pa.save(update_fields=['status'])
    return {'ok': True, 'status': 200, 'reply': "Yaxshi, bekor qildim. 👍"}


def _success_reply(pa):
    """Bajarilgan amal uchun qisqa o'zbekcha javob (result ichida bo'lsa — o'sha)."""
    if isinstance(pa.result, dict) and pa.result.get('reply'):
        return pa.result['reply']
    return "Bajarildi! ✅"
