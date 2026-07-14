"""Rasmsiz katalog mahsulotlariga toza placeholder rasm generatsiya qiladi.

    python manage.py gen_catalog_placeholders            # rasmsizlarga generatsiya
    python manage.py gen_catalog_placeholders --dry-run  # sanaydi, yozmaydi
    python manage.py gen_catalog_placeholders --force    # rasmi borlarni ham qayta

Nega placeholder: haqiqiy brend qadog'i fotosi tashqi yuklashni (mualliflik
xavfi) talab qiladi. Placeholder — internetsiz, xavfsiz, mahsulot nomi +
kategoriya rangli toza plitka. Keyin admin/egasi xohlagan mahsulotni haqiqiy
foto bilan almashtiradi (bu buyruq faqat rasmsizlarga tegadi — idempotent).

Rasmlar xotirada (PIL) generatsiya qilinib, Django storage API orqali
saqlanadi — lokal FS ham, Supabase S3 ham ishlaydi (import_catalog kabi).
"""
import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from delivery.models import CatalogProduct

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    Image = None

SS = 2          # supersampling — silliq chekkalar uchun 2x chizib, so'ng kichraytiriladi
SIZE = 800      # yakuniy tomon (px)

# Kategoriya -> asosiy rang (RGB). Topilmasa nom/kategoriya hash'idan palitra.
CATEGORY_COLORS = {
    'Ichimliklar': (37, 99, 235),        # ko'k
    'Oziq-ovqat': (217, 119, 6),         # sarg'ish
    'Non mahsulotlari': (180, 83, 9),    # jigarrang
    "Go'zallik": (219, 39, 119),         # pushti
    "Uy-ro'zg'or": (13, 148, 136),       # firuza
    'Bolalar': (124, 58, 237),           # binafsha
}
PALETTE = [
    (37, 99, 235), (217, 119, 6), (180, 83, 9), (219, 39, 119),
    (13, 148, 136), (124, 58, 237), (5, 150, 105), (220, 38, 38),
]
GENERIC_BRANDS = {'SamCity', 'Local Farm', 'Local Bakery', ''}

_INK = (31, 41, 55)      # slate-800 — nom matni
_MUTED = (107, 114, 128)  # gray-500 — brend matni

# Turli platformalarda ishlashi uchun shrift nomzodlari (Windows + Linux).
_FONT_BOLD = [
    'C:/Windows/Fonts/arialbd.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    'DejaVuSans-Bold.ttf', 'arialbd.ttf',
]
_FONT_REG = [
    'C:/Windows/Fonts/arial.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    'DejaVuSans.ttf', 'arial.ttf',
]


def _font(candidates, size):
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _clean(text):
    """Mojibake (U+FFFD) va ortiqcha bo'shliqlarni tozalaydi."""
    return ' '.join((text or '').replace('�', ' ').split())


def _initials(name):
    """Har so'zning birinchi ALIFBO harfi (2 tagacha); o'lcham tokenlari
    ("1L", "50g", "3.2%") va tinish belgilari (« ( ) tashlab yuboriladi."""
    letters = []
    for w in _clean(name).split():
        if w[:1].isdigit():   # o'lcham/miqdor tokeni — bosh harfga kirmaydi
            continue
        for ch in w:
            if ch.isalpha():
                letters.append(ch)
                break
        if len(letters) >= 2:
            break
    return ''.join(letters[:2]).upper() or '?'


def _color_for(product):
    cat = product.category.name if product.category else ''
    if cat in CATEGORY_COLORS:
        return CATEGORY_COLORS[cat]
    key = cat or product.name or ''
    return PALETTE[sum(map(ord, key)) % len(PALETTE)]


def _tint(color, amount=0.90):
    """Rangni oq bilan aralashtiradi (fon uchun ochiq tus)."""
    return tuple(int(c * (1 - amount) + 255 * amount) for c in color)


def _wrap(draw, text, font, max_w):
    lines, cur = [], ''
    for word in text.split():
        trial = f'{cur} {word}'.strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _render(product):
    """Bitta mahsulot uchun 800x800 WEBP placeholder baytlarini qaytaradi."""
    color = _color_for(product)
    s = SIZE * SS
    im = Image.new('RGB', (s, s), _tint(color))
    d = ImageDraw.Draw(im)

    # ── Kategoriya yorlig'i (tepada) ──
    cat = _clean(product.category.name if product.category else '')
    if cat:
        cf = _font(_FONT_BOLD, 26 * SS)
        cw = d.textlength(cat.upper(), font=cf)
        d.text(((s - cw) / 2, 60 * SS), cat.upper(), font=cf, fill=color)

    # ── Markaziy doira + bosh harflar ──
    r = 170 * SS
    cx, cy = s / 2, 300 * SS
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    initf = _font(_FONT_BOLD, 150 * SS)
    ini = _initials(product.name)
    bb = d.textbbox((0, 0), ini, font=initf)
    d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]),
           ini, font=initf, fill=(255, 255, 255))

    # ── Mahsulot nomi (o'ralgan, ≤3 qator) ──
    namef = _font(_FONT_BOLD, 46 * SS)
    lines = _wrap(d, _clean(product.name), namef, s - 120 * SS)
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1].rstrip('.') + '…'
    y = 520 * SS
    for ln in lines:
        w = d.textlength(ln, font=namef)
        d.text(((s - w) / 2, y), ln, font=namef, fill=_INK)
        y += 60 * SS

    # ── Brend (umumiy bo'lmasa) ──
    brand = _clean(product.brand)
    if brand not in GENERIC_BRANDS:
        bf = _font(_FONT_REG, 34 * SS)
        bw = d.textlength(brand, font=bf)
        d.text(((s - bw) / 2, y + 14 * SS), brand, font=bf, fill=_MUTED)

    im = im.resize((SIZE, SIZE), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'WEBP', quality=88, method=6)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Rasmsiz katalog mahsulotlariga toza placeholder rasm generatsiya qiladi."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Hech narsa yozmasdan nechта ekanini sanaydi')
        parser.add_argument('--force', action='store_true',
                            help='Rasmi bor mahsulotlarni ham qayta generatsiya qiladi')

    def handle(self, *args, **opts):
        if Image is None:
            self.stderr.write(self.style.ERROR(
                "Pillow o'rnatilmagan. `pip install pillow` qiling."))
            return

        qs = CatalogProduct.objects.all().order_by('category__name', 'name')
        if not opts['force']:
            qs = qs.filter(image__in=['', None])

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                "Rasmsiz mahsulot yo'q — hammasida rasm bor."))
            return

        dry = opts['dry_run']
        self.stdout.write(f"{'[DRY-RUN] ' if dry else ''}{total} ta mahsulotga "
                          f"placeholder generatsiya qilinadi...\n")

        done = 0
        for p in qs.iterator():
            if dry:
                self.stdout.write(f"  - {p.name}  [{_initials(p.name)}]")
                continue
            try:
                blob = _render(p)
                slug = slugify(p.name) or f'catalog-{p.pk}'
                p.image.save(f'{slug}.webp', ContentFile(blob), save=True)
                done += 1
                self.stdout.write(f"  OK  {p.name}")
            except Exception as e:  # bitta mahsulot xatosi butun jarayonni to'xtatmasin
                self.stderr.write(self.style.WARNING(f"  XATO {p.name} — {e}"))

        if dry:
            self.stdout.write(self.style.SUCCESS(f"\n[DRY-RUN] {total} ta tayyor (yozilmadi)."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n{done}/{total} ta placeholder generatsiya qilindi."))
