import os
import functools
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.http import JsonResponse, HttpResponse

# Allowed image extensions and MIME-style headers
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
MAX_FILE_SIZE_MB = 5


def validate_file_type(file):
    """Validates that an uploaded file is a real image and within size limits."""
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"Noma'lum fayl formati: '{ext}'. Faqat rasm yuklang.")
    if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Fayl hajmi juda katta. Maksimal hajm: {MAX_FILE_SIZE_MB}MB.")
    return True


def parse_int(val):
    """Safely parse an integer from a string, ignoring spaces and commas."""
    try:
        return int(str(val).replace(' ', '').replace(',', ''))
    except (ValueError, TypeError):
        return None


def ratelimit(key, limit=60, window=60, methods=None):
    """Simple cache-based per-user/IP rate limiter.

    Usage:
        @ratelimit('loc', limit=40, window=60)
        def view(request): ...
        @ratelimit('login', limit=10, window=300, methods=('POST',))
        def view(request): ...

    `methods` (optional): only count/limit these HTTP methods (e.g. ('POST',));
    other methods pass through unthrottled — useful for views that also serve a
    GET form page. Returns HTTP 429 when the limit is exceeded within `window`
    (seconds). Falls open (allows the request) if the cache backend is unavailable.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if methods and request.method not in methods:
                return view_func(request, *args, **kwargs)
            try:
                if request.user.is_authenticated:
                    ident = f'u{request.user.id}'
                else:
                    ident = 'ip' + (request.META.get('REMOTE_ADDR', 'anon'))
                cache_key = f'rl:{key}:{ident}'
                count = cache.get(cache_key, 0)
                if count >= limit:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                       request.content_type == 'application/x-www-form-urlencoded':
                        return JsonResponse({'ok': False, 'error': 'rate_limited'}, status=429)
                    return HttpResponse('Too many requests', status=429)
                # add() sets only if missing (starts the window); then incr.
                if not cache.add(cache_key, 1, window):
                    try:
                        cache.incr(cache_key)
                    except ValueError:
                        cache.set(cache_key, 1, window)
            except Exception:
                pass  # never block a request because the limiter errored
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def get_initials(name_or_phone):
    """Return 1-2 letter initials from a name or phone number."""
    name = name_or_phone or ''
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper() if name else '??'
