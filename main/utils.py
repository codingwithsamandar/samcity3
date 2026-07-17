import os
import json
import functools
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.http import JsonResponse, HttpResponse
from django.utils.safestring import mark_safe

# Allowed image extensions and MIME-style headers
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
MAX_FILE_SIZE_MB = 5
# Piksel chegarasi. Hajm chegarasi (5MB) buni USHLAMAYDI: siqilgan rasm kichkina
# bo'lib, ochilganda ulkan bo'lishi mumkin (dekompressiya bombasi). Sinovda
# 164KB lik PNG o'zini 13000x13000 (169 MP) deb e'lon qilib o'tib ketdi — u
# dekodlansa ~484MB RAM oladi. 80 MP eng yirik telefon kamerasidan ham katta.
MAX_IMAGE_PIXELS = 80_000_000


def safe_json(value):
    """HTML `<script>` ichiga qo'yish uchun xavfsiz JSON.

    `json.dumps` `<`, `>`, `&`, U+2028/U+2029 belgilarni escape qilmaydi —
    ma'lumot ichida `</script>` bo'lsa, XSS chiqib ketishi mumkin. Bu yordamchi
    Django'ning `json_script` bilan bir xil qoidada ularni \\u ko'rinishiga
    o'tkazadi va `mark_safe` bilan qaytaradi (template'da `|safe` bilan ishlaydi).
    """
    dumped = json.dumps(value)
    # Django json_script bilan bir xil belgilar: < > & U+2028 U+2029
    for _cp in (0x3c, 0x3e, 0x26, 0x2028, 0x2029):
        dumped = dumped.replace(chr(_cp), '\\u%04x' % _cp)
    return mark_safe(dumped)


def validate_file_type(file):
    """Validates that an uploaded file is a real image and within size limits.

    Kengaytma va hajmdan tashqari fayl MAZMUNI ham tekshiriladi: Pillow bilan
    haqiqiy rasm ekanligi tasdiqlanadi. Bu `.jpg` deb nomlangan lekin ichida
    HTML/skript bo'lgan yoki buzuq fayllarni bloklaydi (polyglot/upload XSS).
    """
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"Noma'lum fayl formati: '{ext}'. Faqat rasm yuklang.")
    if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Fayl hajmi juda katta. Maksimal hajm: {MAX_FILE_SIZE_MB}MB.")
    # Mazmun tekshiruvi: fayl chindan ham rasm ekanini Pillow tasdiqlaydi.
    try:
        from PIL import Image
        pos = file.tell() if hasattr(file, 'tell') else None
        try:
            im = Image.open(file)
            # Piksel chegarasi verify() dan OLDIN va o'lchamni O'QIB tekshiriladi:
            # Image.verify() JPEG/GIF/WEBP uchun amalda hech nima qilmaydi (uni
            # faqat PNG qayta belgilaydi), shuning uchun sarlavhasida ulkan
            # o'lcham e'lon qilgan kichkina fayl bemalol o'tib ketardi.
            # `Image.open` faqat sarlavhani o'qiydi — bu yerda hali RAM yeyilmaydi.
            w, h = im.size
            if w * h > MAX_IMAGE_PIXELS:
                raise ValidationError(
                    f"Rasm o'lchami juda katta: {w}x{h}. "
                    f"Maksimal {MAX_IMAGE_PIXELS // 1_000_000} megapiksel.")
            im.verify()
        finally:
            if pos is not None and hasattr(file, 'seek'):
                file.seek(pos)
    except ImportError:
        # Pillow yo'q bo'lsa — kengaytma+hajm tekshiruvi bilan cheklaymiz.
        pass
    except ValidationError:
        raise  # o'z xabarimiz quyidagi umumiy xabarga aylanib ketmasin
    except Exception:
        raise ValidationError("Fayl haqiqiy rasm emas yoki buzilgan.")
    return True


def check_images(*files):
    """Bir nechta yuklangan rasmni tekshiradi. Yaroqsizi bo'lsa xato MATNI, aks holda None.

    Nima uchun kerak: model maydonidagi `validators=[validate_file_type]` FAQAT
    `full_clean()` da ishlaydi — `objects.create()` va `.save()` uni butunlay
    chetlab o'tadi. Django admin va ModelForm full_clean chaqiradi, API va
    qo'lda yozilgan view'lar esa yo'q. Shuning uchun har bir API kirish nuqtasi
    buni OCHIQ chaqirishi shart; maydondagi validator u yerda hujjat, himoya emas.
    """
    for f in files:
        if not f:
            continue
        try:
            validate_file_type(f)
        except ValidationError as e:
            return '; '.join(e.messages)
    return None


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
