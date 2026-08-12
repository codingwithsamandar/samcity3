"""Tashqi qidiruv agregatori — yoqilgan providerlardan PARALLEL e'lon yig'adi.

`ads.search` faqat shu `search()` ni chaqiradi. Providerlar bir vaqtда (thread)
ishlaydi — 3-4 sayt bo'lса ham asistent kutдирмаydi. Har biriга alohida timeout,
umumiyга ham chegara. Xatoga to'liq chidamli: muammода bo'sh ro'yxat.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings

from . import base
# Providerlarni import qilish — ular o'zini reyestrga qo'shadi.
from . import olx, uybor, avtoelon, pending          # ads domeni  # noqa: F401
from . import hh, olx_jobs, jobs_pending             # jobs domeni  # noqa: F401

log = logging.getLogger(__name__)

_CACHE_TTL = 300  # sekund

# Domen → qaysi settings kaliti yoqilgan providerlar ro'yxatini beradi.
_KEYS_SETTING = {
    'ads': 'ASSISTANT_EXTERNAL_PROVIDERS',
    'jobs': 'ASSISTANT_EXTERNAL_JOB_PROVIDERS',
}


def is_enabled():
    return bool(getattr(settings, 'ASSISTANT_EXTERNAL_SEARCH_ENABLED', True))


def _provider_keys(domain):
    keys = getattr(settings, _KEYS_SETTING.get(domain, ''), None)
    if not keys:
        return None
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split(',') if k.strip()]
    return list(keys)


def _cache_key(domain, query, limit, category):
    return f"ext_search:{domain}:{(query or '').strip().lower()}:{limit}:{category or ''}"


def _run(provider, query, limit, category):
    try:
        return provider.search(query, limit=limit, category=category) or []
    except Exception as e:  # noqa: BLE001
        log.warning('Tashqi provider %s xatosi: %s', getattr(provider, 'key', '?'), e)
        return []


def search(query, limit=6, category=None, domain='ads'):
    """Yoqilgan tashqi providerlardan `ExternalListing` ro'yxati (parallel).

    `domain` — 'ads' (oldi-sotdi) yoki 'jobs' (ish). Faqat so'rovга MOS providerlar
    chaqiriladi (`applies`). Natija keshlanadi. Takror (bir xil url) o'chiriladi.
    """
    query = (query or '').strip()
    if not is_enabled() or not query:
        return []

    ck = _cache_key(domain, query, limit, category)
    cache = None
    try:
        from django.core.cache import cache as _cache
        cache = _cache
        cached = cache.get(ck)
        if cached is not None:
            return cached
    except Exception:  # noqa: BLE001
        cache = None

    providers = [p for p in base.get_providers(_provider_keys(domain), domain=domain)
                 if p.applies(query, category)]
    if not providers:
        return []

    results, timeout = [], float(getattr(settings, 'ASSISTANT_EXTERNAL_TIMEOUT', 4))
    try:
        with ThreadPoolExecutor(max_workers=min(6, len(providers))) as ex:
            futs = {ex.submit(_run, p, query, limit, category): p for p in providers}
            for fut in as_completed(futs, timeout=timeout + 1):
                try:
                    results.extend(fut.result() or [])
                except Exception:  # noqa: BLE001
                    pass
    except Exception as e:  # noqa: BLE001 — timeout va h.k.
        log.warning('Tashqi qidiruv agregator xatosi: %s', e)

    # Takrorни o'chirish (url bo'yicha) + umumiy chegara.
    seen, deduped = set(), []
    for r in results:
        u = getattr(r, 'url', '')
        if u in seen:
            continue
        seen.add(u)
        deduped.append(r)
    deduped = deduped[:limit]

    if cache is not None:
        try:
            cache.set(ck, deduped, _CACHE_TTL)
        except Exception:  # noqa: BLE001
            pass
    return deduped
