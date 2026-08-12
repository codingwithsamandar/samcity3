"""AgentTask holat mashinasi — bir necha gap davomida davom etadigan vazifa.

Nega kerak: LLM ga butun suhbatni qayta yuborish o'rniga ixcham holat (slots +
missing) saqlanadi. Token kam, AI adashmaydi, suhbat uzilsa davom ettirish mumkin.

Muddati o'tgan (2 soat — models.TASK_TTL_HOURS) vazifa `abandoned` ga o'tadi.
Foydalanuvchi qaytsa: «Lavash buyurtmangiz yarim qolgan edi, davom etamizmi?»
"""

from django.db.models import Q
from django.utils import timezone


def _owner_filter(ctx):
    """Vazifa egasi bo'yicha filtr: kirgan bo'lsa user, aks holda session_key."""
    if ctx is not None and ctx.is_authenticated:
        return Q(user=ctx.user)
    if ctx is not None and ctx.session_key:
        return Q(session_key=ctx.session_key, user__isnull=True)
    return None


def active_task(ctx, goal=None):
    """Joriy faol (muddati o'tmagan) vazifani qaytaradi yoki None.

    Muddati o'tgan faol vazifalarni `abandoned` ga o'tkazadi (yon ta'sir).
    """
    from .models import AgentTask
    owner = _owner_filter(ctx)
    if owner is None:
        return None
    qs = AgentTask.objects.filter(owner, status='active')
    if goal:
        qs = qs.filter(goal=goal)

    now = timezone.now()
    for t in qs.order_by('-updated_at'):
        if t.expires_at and t.expires_at <= now:
            t.status = 'abandoned'
            t.save(update_fields=['status'])
            continue
        return t
    return None


def get_or_create_active(ctx, goal, missing=None, state=''):
    """Berilgan maqsad uchun faol vazifani oladi yoki yaratadi."""
    from .models import AgentTask
    existing = active_task(ctx, goal=goal)
    if existing is not None:
        return existing
    return AgentTask.objects.create(
        user=(ctx.user if (ctx and ctx.is_authenticated) else None),
        session_key=(ctx.session_key if ctx else '') or '',
        goal=goal[:40], state=state[:40], missing=list(missing or []),
    )


def set_slot(task, key, value, save=True):
    """Bitta maydonni yozadi va `missing` dan olib tashlaydi."""
    task.set_slot(key, value)
    if save:
        task.save(update_fields=['slots', 'missing', 'updated_at'])
    return task


def set_state(task, state, save=True):
    task.state = (state or '')[:40]
    if save:
        task.save(update_fields=['state', 'updated_at'])
    return task


def next_missing(task):
    """Hali yetishmayotgan birinchi maydon (AI aynan shuni so'raydi) yoki None."""
    missing = task.missing or []
    return missing[0] if missing else None


def is_ready(task):
    """Barcha kerakli maydonlar to'langanmi."""
    return not (task.missing or [])


def remember_selection(task, ref, save=True):
    """Oxirgi ekran ro'yxati ref'ini eslab qoladi (selection uchun)."""
    task.last_ui_ref = (ref or '')[:32]
    if save:
        task.save(update_fields=['last_ui_ref', 'updated_at'])
    return task


def complete(task, save=True):
    task.status = 'done'
    if save:
        task.save(update_fields=['status', 'updated_at'])
    return task


def abandon(task, save=True):
    task.status = 'abandoned'
    if save:
        task.save(update_fields=['status', 'updated_at'])
    return task
