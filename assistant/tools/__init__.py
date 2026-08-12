"""Tool modullari — import qilinishi bilan reyestrga (registry) yoziladi.

Yangi bo'lim qo'shish: shu papkaga `<bo'lim>.py` yozing va quyidagi `_MODULES`
ro'yxatiga qo'shing. `assistant.apps.AssistantConfig.ready()` ularni Django
ishga tushganda avtomatik import qiladi.

0-to'lqin: places (o'qish namunasi) va delivery (yozish + tasdiq namunasi).
"""

_MODULES = ['places', 'delivery', 'booking', 'ads', 'jobs', 'community', 'taxi',
            'account']

# Taksi arxivlangan — settings.TAXI_ENABLED=False bo'lsa `taxi` tool moduli
# UMUMAN import qilinmaydi. Natijada registry'da taxi amallari bo'lmaydi va
# `registry.tool_specs()` o'sha bo'limni LLM sxemasiga qo'shmaydi (bo'sh bo'lim
# tashlab ketiladi) — ya'ni AI agent orqali ham taksi chaqirilmaydi.
def _enabled_modules():
    from django.conf import settings
    if settings.TAXI_ENABLED:
        return _MODULES
    return [m for m in _MODULES if m != 'taxi']


def load_all():
    """Barcha tool modullarini import qiladi (reyestrga yig'ish). Xatoga chidamli."""
    import importlib
    for name in _enabled_modules():
        try:
            importlib.import_module(f'{__name__}.{name}')
        except Exception:  # noqa: BLE001 — bitta modul buzilsa ham qolganini yuklaymiz
            import logging
            logging.getLogger('assistant').exception('tool moduli yuklanmadi: %s', name)
