import io
import os
import json
import functools
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpResponse
from django.utils.safestring import mark_safe

# Allowed image extensions and MIME-style headers
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
# 5MB edi — bu oddiy telefon rasmini ham RAD ETARDI: o'lchandi, 12 MP / sifat 90
# JPEG = ~6.5MB, 24 MP = ~13MB. Ya'ni foydalanuvchi rasm yuklolmasdi. Endi
# yuklangach `downscale_image` uni ~150-400KB ga tushiradi, shuning uchun katta
# kirishni qabul qilish xavfsiz. Bombalardan `MAX_IMAGE_PIXELS` himoya qiladi,
# dekodlash RAM'ini esa JPEG uchun `Image.draft()` past ushlab turadi.
# (`DATA_UPLOAD_MAX_MEMORY_SIZE` fayllarga taalluqli emas — ular alohida.)
MAX_FILE_SIZE_MB = 12
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


def downscale_image(f, max_dim=1600, quality=82):
    """Rasmni `max_dim` ichiga siqadi. Yangi fayl obyektini yoki ORIGINALNI qaytaradi.

    Nima uchun: telefon rasmi 4000x3000 / 5MB bo'ladi, biz esa uni 100-1000px
    katakda ko'rsatamiz. Shofirkonda mobil internetdan 6 ta shunday rasm ~30MB.
    1600px @ q82 odatda ~90% ni qirqadi.

    Muhim qoidalar (adversarial tekshiruvda aniqlangan):
    * FORMAT SAQLANADI. JPEG'ga majburlash shaffof PNG logo'ni `OSError: cannot
      write mode RGBA as JPEG` qiladi, `.convert('RGB')` esa uni qora quti qiladi.
      Format saqlansa kengaytma ham o'zgarmaydi — S3 ContentType nomdan olinadi.
    * GIF'ga tegilmaydi (animatsiya yo'qoladi).
    * YANGI obyekt qaytariladi, original mutatsiya QILINMAYDI: `file.file` ni
      BytesIO bilan almashtirish FileSystemStorage'da >2.5MB yuklamalarni
      buzadi (TemporaryUploadedFile.temporary_file_path() -> AttributeError),
      S3'da esa ishlaydi — ya'ni dev'da yiqilib, prod'da o'tib ketadigan farq.
    * Har qanday xatoda original qaytariladi — kichraytirish yuklashni
      hech qachon buzmasligi kerak.

    Chaqirishdan OLDIN `validate_file_type` o'tgan bo'lishi shart (u piksel
    chegarasini tekshiradi — bu yerda dekod qilamiz).
    """
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return f
    name = getattr(f, 'name', '') or ''
    ext = os.path.splitext(name)[1].lower()
    if ext == '.gif':
        return f
    try:
        pos = f.tell() if hasattr(f, 'tell') else None
        try:
            im = Image.open(f)
            fmt = im.format                     # 'JPEG' | 'PNG' | 'WEBP'
            if not fmt or fmt == 'GIF':
                return f
            if max(im.size) <= max_dim:
                return f                        # allaqachon kichik — tegmaymiz
            if fmt == 'JPEG':
                # JPEG'ni to'liq o'lchamda dekod QILMAYMIZ: draft() uni DCT
                # darajasida 1/2..1/8 ga kichraytirib ochadi. Render free tier'da
                # (512MB) bu hal qiluvchi — 24 MP foto to'liq ochilsa ~72MB RAM.
                im.draft('RGB', (max_dim, max_dim))
            im = ImageOps.exif_transpose(im)    # telefon rasmi yonboshlab qolmasin
            im.thumbnail((max_dim, max_dim), Image.LANCZOS)
            buf = io.BytesIO()
            save_kw = {'optimize': True}
            if fmt == 'JPEG':
                save_kw['quality'] = quality
                save_kw['progressive'] = True
                if im.mode not in ('RGB', 'L'):
                    im = im.convert('RGB')      # JPEG alfa qo'llamaydi
            elif fmt == 'WEBP':
                save_kw['quality'] = quality
            im.save(buf, fmt, **save_kw)
        finally:
            if pos is not None and hasattr(f, 'seek'):
                f.seek(pos)
        data = buf.getvalue()
        if len(data) >= getattr(f, 'size', len(data) + 1):
            return f                            # kichraymadi — originalni qoldiramiz
        return ContentFile(data, name=name)
    except Exception:
        return f


# Profillar: rasm nima uchun ishlatilishiga qarab.
#   PHOTO   — galereya/e'lon fotosi, katta ko'rsatiladi
#   PORTRAIT— avatar/egasi rasmi, kichik doira
#   LOGO    — do'kon/xizmat logosi; shaffoflik saqlanadi (format o'zgarmagani uchun)
IMAGE_PROFILES = {
    'photo': (1600, 82),
    'portrait': (1024, 82),
    'logo': (512, 88),
}


def clean_image(f, profile='photo'):
    """Yuklangan rasmni TEKSHIRADI va kichraytirib qaytaradi.

    Yaroqsiz bo'lsa `ValidationError` (validate_file_type bilan bir xil).
    Chaqiruvchi QAYTGAN qiymatni ishlatishi shart:

        img = clean_image(request.FILES['logo'], 'logo')
        store.logo = img

    Nega qaytariladi, mutatsiya emas: yuklangan faylning ichki `file` ini
    almashtirish >2.5MB yuklamalarda FileSystemStorage'ni yiqitadi
    (TemporaryUploadedFile.temporary_file_path() -> AttributeError), S3'da esa
    ishlaydi — dev'da yiqilib prod'da o'tib ketadigan farq.
    """
    if not f:
        return f
    validate_file_type(f)          # piksel chegarasi shu yerda — dekoddan oldin
    max_dim, quality = IMAGE_PROFILES.get(profile, IMAGE_PROFILES['photo'])
    return downscale_image(f, max_dim, quality)


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
