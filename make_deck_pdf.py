# -*- coding: utf-8 -*-
"""
SamCity Investor Deck -> PDF (12 slayd).

Faqat Python standart kutubxonasi (pip install shart emas).
Ishga tushirish:   python make_deck_pdf.py
Natija:            SamCity_Investor_Deck.pdf
"""

import zlib
import os
import sys

W, H = 960.0, 540.0
ML, MR = 52.0, 52.0
MT = 40.0
CW = W - ML - MR

NAVY   = (0.043, 0.122, 0.227)
NAVY2  = (0.071, 0.192, 0.361)
INK    = (0.051, 0.106, 0.165)
BODY   = (0.208, 0.290, 0.380)
MUTED  = (0.420, 0.506, 0.600)
LINE   = (0.874, 0.906, 0.937)
CARDBG = (0.984, 0.988, 0.996)
HEADBG = (0.949, 0.965, 0.980)
TEAL   = (0.055, 0.624, 0.557)
AMBER  = (0.961, 0.651, 0.137)
RED    = (0.851, 0.325, 0.310)
GREEN  = (0.118, 0.620, 0.353)
WHITE  = (1.0, 1.0, 1.0)

DCARD  = (0.145, 0.212, 0.318)
DEDGE  = (0.28, 0.35, 0.45)
DTEXT  = (0.80, 0.86, 0.91)
DSUB   = (0.72, 0.79, 0.86)

REDBG   = (0.984, 0.925, 0.925)
GREENBG = (0.914, 0.969, 0.957)

PILL = {
    'ok':  ((0.890, 0.961, 0.922), (0.075, 0.455, 0.271)),
    'mid': ((0.992, 0.945, 0.863), (0.604, 0.400, 0.031)),
    'no':  ((0.984, 0.906, 0.906), (0.651, 0.196, 0.184)),
}

_HELV = {
    32:278, 33:278, 34:355, 35:556, 36:556, 37:889, 38:667, 39:191, 40:333, 41:333,
    42:389, 43:584, 44:278, 45:333, 46:278, 47:278, 48:556, 49:556, 50:556, 51:556,
    52:556, 53:556, 54:556, 55:556, 56:556, 57:556, 58:278, 59:278, 60:584, 61:584,
    62:584, 63:556, 64:1015, 65:667, 66:667, 67:722, 68:722, 69:667, 70:611, 71:778,
    72:722, 73:278, 74:500, 75:667, 76:556, 77:833, 78:722, 79:778, 80:667, 81:778,
    82:722, 83:667, 84:611, 85:722, 86:667, 87:944, 88:667, 89:667, 90:611, 91:278,
    92:278, 93:278, 94:469, 95:556, 96:333, 97:556, 98:556, 99:500, 100:556, 101:556,
    102:278, 103:556, 104:556, 105:222, 106:222, 107:500, 108:222, 109:833, 110:556,
    111:556, 112:556, 113:556, 114:333, 115:500, 116:278, 117:556, 118:500, 119:722,
    120:500, 121:500, 122:500, 123:334, 124:260, 125:334, 126:584,
    146:191, 149:350, 151:1000, 183:278,
}
_HELVB = {
    32:278, 33:333, 34:474, 35:556, 36:556, 37:889, 38:722, 39:238, 40:333, 41:333,
    42:389, 43:584, 44:278, 45:333, 46:278, 47:278, 48:556, 49:556, 50:556, 51:556,
    52:556, 53:556, 54:556, 55:556, 56:556, 57:556, 58:333, 59:333, 60:584, 61:584,
    62:584, 63:611, 64:975, 65:722, 66:722, 67:722, 68:722, 69:667, 70:611, 71:778,
    72:722, 73:278, 74:556, 75:722, 76:611, 77:833, 78:722, 79:778, 80:667, 81:778,
    82:722, 83:667, 84:611, 85:722, 86:667, 87:944, 88:667, 89:667, 90:611, 91:333,
    92:278, 93:333, 94:584, 95:556, 96:333, 97:556, 98:611, 99:556, 100:611, 101:556,
    102:333, 103:611, 104:611, 105:278, 106:278, 107:556, 108:278, 109:889, 110:611,
    111:611, 112:611, 113:611, 114:389, 115:556, 116:333, 117:611, 118:556, 119:778,
    120:556, 121:556, 122:500, 123:389, 124:280, 125:389, 126:584,
    146:238, 149:350, 151:1000, 183:278,
}


# Unicode -> WinAnsi (cp1252) moslashtirish jadvali.
# Muhim: manba kodida yozilgan '’' aslida U+0092 (boshqaruv belgisi) bo'lib,
# cp1252 uni kodlay olmaydi va '?' chiqadi. Shuning uchun uni to'g'ri
# apostrofga (U+2019) o'giramiz. Qolgan belgilar ham xavfsiz muqobil bilan
# almashtiriladi.
_XLAT = {
    0x0092: u'’',   # noto'g'ri kodlangan apostrof -> to'g'ri apostrof
    0x02BB: u'’',   # o'zbek okinasi (o' va g' harflarida)
    0x02BC: u'’',
    0x2018: u'’',   # chap qo'shtirnoq -> o'ng
    0x2032: u'’',
    0x0060: u"'",        # teskari apostrof
    0x201C: u'"', 0x201D: u'"', 0x201E: u'"',
    0x2013: u'-', 0x2014: u'-', 0x2212: u'-',   # tire turlari
    0x2192: u'->', 0x2190: u'<-',
    0x2265: u'>=', 0x2264: u'<=',
    0x2026: u'...',
    0x00A0: u' ',        # uzilmas probel
    0x2022: u'·',   # bullet -> middot
}


def _tobytes(s):
    if isinstance(s, bytes):
        return s
    return s.translate(_XLAT).encode('cp1252', 'replace')


def text_width(s, size, bold=False):
    tbl = _HELVB if bold else _HELV
    return sum(tbl.get(ch, 556) for ch in _tobytes(s)) * size / 1000.0


def wrap(s, size, maxw, bold=False):
    out = []
    for para in str(s).split('\n'):
        words = para.split()
        if not words:
            out.append('')
            continue
        cur = words[0]
        for w in words[1:]:
            if text_width(cur + ' ' + w, size, bold) <= maxw:
                cur += ' ' + w
            else:
                out.append(cur)
                cur = w
        out.append(cur)
    return out


# ─────────────────────────────────────────── JPEG o'qish (rasm qo'yish uchun)

_JPEG_CACHE = {}
_SOF = (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
        0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)


def jpeg_info(path):
    """(kenglik, balandlik, kanal_soni, xom_baytlar) yoki None.

    JPEG PDF ichiga qayta kodlanmasdan, DCTDecode filtri bilan to'g'ridan
    joylashtiriladi - shuning uchun bizga faqat o'lcham va kanal soni kerak.
    """
    if path in _JPEG_CACHE:
        return _JPEG_CACHE[path]
    res = None
    try:
        with open(path, 'rb') as f:
            data = f.read()
        if data[:2] == b'\xff\xd8':
            i, n = 2, len(data)
            while i < n - 1:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                i += 2
                if marker == 0xD8 or marker == 0x01 or 0xD0 <= marker <= 0xD7:
                    continue
                if marker == 0xD9 or i + 2 > n:
                    break
                seglen = (data[i] << 8) | data[i + 1]
                if marker in _SOF and i + 7 < n:
                    h = (data[i + 3] << 8) | data[i + 4]
                    w = (data[i + 5] << 8) | data[i + 6]
                    res = (w, h, data[i + 7], data)
                    break
                i += seglen
    except (OSError, IndexError):
        res = None
    _JPEG_CACHE[path] = res
    return res


class Page(object):
    def __init__(self):
        self.ops = []
        self.imgs = {}          # nom -> fayl yo'li

    def _col(self, c, stroke=False):
        self.ops.append('%.4f %.4f %.4f %s' % (c[0], c[1], c[2],
                                               'RG' if stroke else 'rg'))

    def rect(self, x, y, w, h, fill=None, stroke=None, lw=1.0):
        if w <= 0 or h <= 0:
            return
        if fill:
            self._col(fill)
        if stroke:
            self._col(stroke, True)
            self.ops.append('%.2f w' % lw)
        self.ops.append('%.2f %.2f %.2f %.2f re' % (x, y, w, h))
        self.ops.append('B' if (fill and stroke) else ('f' if fill else 'S'))

    def text(self, s, x, y, size, color=INK, bold=False, char_space=0.0):
        if not s:
            return
        esc = bytearray()
        for ch in _tobytes(s):
            if ch in (0x28, 0x29, 0x5C):
                esc += b'\\'
            esc.append(ch)
        self._col(color)
        self.ops.append('BT %s %.2f Tf %.2f Tc %.2f %.2f Td (%s) Tj ET'
                        % ('/F2' if bold else '/F1', size, char_space, x, y,
                           esc.decode('cp1252')))

    def text_center(self, s, cx, y, size, color=INK, bold=False):
        self.text(s, cx - text_width(s, size, bold) / 2.0, y, size, color, bold)

    def para(self, s, x, y, size, maxw, color=BODY, bold=False, leading=None):
        lead = leading or (size * 1.42)
        yy = y
        for ln in wrap(s, size, maxw, bold):
            self.text(ln, x, yy, size, color, bold)
            yy -= lead
        return yy + lead

    def image(self, path, x, y, w, h):
        """Rasmni (x, y) - pastki chap burchakdan w x h maydonga joylaydi.

        'cover' rejimi: nisbat buzilmaydi, ortiqcha qismi kesiladi (markazdan).
        Rasm topilmasa yoki JPEG bo'lmasa - False qaytaradi.
        """
        info = jpeg_info(path)
        if not info:
            return False
        iw, ih = info[0], info[1]
        if iw <= 0 or ih <= 0:
            return False
        name = None
        for nm, pth in self.imgs.items():
            if pth == path:
                name = nm
                break
        if name is None:
            name = 'Im%d' % (len(self.imgs) + 1)
            self.imgs[name] = path
        scale = max(w / float(iw), h / float(ih))
        dw, dh = iw * scale, ih * scale
        dx, dy = x - (dw - w) / 2.0, y - (dh - h) / 2.0
        self.ops.append('q %.2f %.2f %.2f %.2f re W n' % (x, y, w, h))
        self.ops.append('%.2f 0 0 %.2f %.2f %.2f cm' % (dw, dh, dx, dy))
        self.ops.append('/%s Do Q' % name)
        return True

    def stream(self):
        return ('\n'.join(self.ops)).encode('cp1252', 'replace')


class PDF(object):
    def __init__(self):
        self.pages = []

    def new_page(self):
        p = Page()
        self.pages.append(p)
        p.index = len(self.pages)      # slayd raqami avtomatik
        return p

    def save(self, path):
        objs = []

        def add(d):
            objs.append(d)
            return len(objs)

        f1 = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica '
                 b'/Encoding /WinAnsiEncoding >>')
        f2 = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold '
                 b'/Encoding /WinAnsiEncoding >>')
        pid = add(b'PLACEHOLDER')

        # Rasmlar - har bir fayl bir marta joylashtiriladi (takrorlanmaydi)
        img_objs = {}
        for pg in self.pages:
            for pth in pg.imgs.values():
                if pth in img_objs:
                    continue
                info = jpeg_info(pth)
                if not info:
                    continue
                iw, ih, ncomp, raw = info
                cs = (b'/DeviceRGB' if ncomp == 3 else
                      b'/DeviceGray' if ncomp == 1 else b'/DeviceCMYK')
                img_objs[pth] = add(
                    b'<< /Type /XObject /Subtype /Image /Width %d /Height %d '
                    b'/ColorSpace %s /BitsPerComponent 8 /Filter /DCTDecode '
                    b'/Length %d >>\nstream\n' % (iw, ih, cs, len(raw))
                    + raw + b'\nendstream')

        kids = []
        for pg in self.pages:
            comp = zlib.compress(pg.stream(), 9)
            cid = add(b'<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(comp)
                      + comp + b'\nendstream')
            xo = b''
            parts = [b'/%s %d 0 R' % (nm.encode('ascii'), img_objs[pth])
                     for nm, pth in pg.imgs.items() if pth in img_objs]
            if parts:
                xo = b'/XObject << ' + b' '.join(parts) + b' >> '
            kids.append(add(
                b'<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] '
                b'/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> %s>> '
                b'/Contents %d 0 R >>' % (pid, W, H, f1, f2, xo, cid)))
        objs[pid - 1] = (b'<< /Type /Pages /Count %d /Kids [%s] >>'
                         % (len(kids), b' '.join(b'%d 0 R' % k for k in kids)))
        cat = add(b'<< /Type /Catalog /Pages %d 0 R >>' % pid)
        info = add(b'<< /Title (SamCity - Investor Deck) /Author (Samandar) >>')

        out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        offs = [0] * (len(objs) + 1)
        for i, d in enumerate(objs, start=1):
            offs[i] = len(out)
            out += b'%d 0 obj\n' % i + d + b'\nendobj\n'
        xref_at = len(out)
        out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
        for i in range(1, len(objs) + 1):
            out += b'%010d 00000 n \n' % offs[i]
        out += (b'trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\n'
                b'startxref\n%d\n%%%%EOF\n' % (len(objs) + 1, cat, info, xref_at))
        with open(path, 'wb') as fh:
            fh.write(bytes(out))


# ─────────────────────────────────────────── Layout

BAND_H = 46.0
BAND_Y = 26.0
FLOOR = BAND_Y + BAND_H + 12      # kontent shu chiziqdan pastga tushmasin


def header(p, tag, title, sub=None, dark=False, tag_color=None):
    tc = tag_color or (AMBER if dark else TEAL)
    y = H - MT - 8
    p.text(tag.upper(), ML, y, 8.5, tc, True, char_space=1.5)
    y -= 28
    p.text(title, ML, y, 24, WHITE if dark else INK, True)
    y -= 22
    if sub:
        y = p.para(sub, ML, y, 10.2, 830, DSUB if dark else MUTED, leading=14.5)
        y -= 18
    else:
        y -= 6
    return y


def band(p, txt, n=None, dark=False):
    """Pastki 'Investor uchun' tasmasi + slayd raqami.

    n berilsa ham e'tiborga olinmaydi — raqam sahifa tartibidan olinadi,
    shunda slayd qo'shilganda qo'lda raqamlashga hojat qolmaydi.
    """
    n = getattr(p, 'index', n or 1)
    p.rect(0, BAND_Y, W, BAND_H, fill=(0.10, 0.22, 0.36) if dark else NAVY)
    lab = 'INVESTOR UCHUN'
    cs = 1.3
    p.text(lab, ML, BAND_Y + BAND_H / 2 - 4, 8.2, AMBER, True, char_space=cs)
    # char_space text_width'ga kirmaydi — qo'lda qo'shamiz, aks holda
    # ajratuvchi chiziq yozuv ustiga tushadi.
    lab_w = text_width(lab, 8.2, True) + len(lab) * cs
    p.rect(ML + lab_w + 16, BAND_Y + 11, 0.8, BAND_H - 22, fill=(0.45, 0.55, 0.65))
    lx = ML + lab_w + 32
    lines = wrap(txt, 10.2, W - lx - MR - 40)
    ty = BAND_Y + BAND_H / 2 + (len(lines) - 1) * 6.5 - 3.5
    for ln in lines:
        p.text(ln, lx, ty, 10.2, (0.92, 0.95, 0.98))
        ty -= 13
    p.text('%02d' % n, W - MR - 12, BAND_Y + BAND_H / 2 - 4, 10, AMBER, True)


def card(p, x, y, w, h, title, body, accent=None, dark=False, bg=None,
         tcol=None, bcol=None, tsize=11.5, bsize=8.9):
    p.rect(x, y - h, w, h, fill=bg or (DCARD if dark else CARDBG),
           stroke=DEDGE if dark else LINE, lw=0.8)
    if accent:
        p.rect(x, y - h, 3.0, h, fill=accent)
    px = x + (14 if accent else 12)
    pw = w - (px - x) - 12
    ty = y - 18
    if title:
        for ln in wrap(title, tsize, pw, True):
            p.text(ln, px, ty, tsize, tcol or (WHITE if dark else INK), True)
            ty -= tsize * 1.24
        ty -= 4
    if body:
        p.para(body, px, ty, bsize, pw, bcol or (DTEXT if dark else BODY),
               leading=bsize * 1.44)


def bullets(p, items, x, y, size, maxw, color=BODY, dark=False, gap=6.0, dot=None):
    dc = dot or TEAL
    yy = y
    for it in items:
        bold_lead = it.startswith('**')
        if bold_lead:
            it = it[2:]
        p.rect(x, yy - 1.5, 5.0, 5.0, fill=dc)
        for i, ln in enumerate(wrap(it, size, maxw - 15)):
            p.text(ln, x + 15, yy, size,
                   (WHITE if dark else INK) if (bold_lead and i == 0)
                   else (DTEXT if dark else color),
                   bold_lead and i == 0)
            yy -= size * 1.4
        yy -= gap
    return yy


def pill(p, x, y, label, kind='ok'):
    bg, fg = PILL[kind]
    w = text_width(label, 7.8, True) + 13
    p.rect(x, y - 3.5, w, 13.5, fill=bg)
    p.text(label, x + 6.5, y, 7.8, fg, True)
    return w


def table(p, x, y, widths, headers, rows, fsize=8.5, pad=6.0):
    total = sum(widths)
    hh = 20.0
    p.rect(x, y - hh, total, hh, fill=HEADBG)
    cx = x
    for i, h in enumerate(headers):
        p.text(h.upper(), cx + pad, y - 13.5, 7.4, NAVY, True, char_space=0.6)
        cx += widths[i]
    p.rect(x, y - hh, total, 1.5, fill=LINE)
    yy = y - hh
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            if isinstance(cell, tuple) and len(cell) == 3 and cell[1] == 'pill':
                cells.append(('pill', (cell[0], cell[2]), False, None))
            else:
                raw = str(cell)
                bold = raw.startswith('**')
                hi = raw.startswith('$$')
                if bold or hi:
                    raw = raw[2:]
                cells.append(('text', wrap(raw, fsize, widths[i] - pad * 2),
                              bold or hi, TEAL if hi else None))
        nl = max(1 if k == 'pill' else len(d) for k, d, _, _ in cells)
        rh = nl * (fsize * 1.42) + pad * 1.9
        cx = x
        for i, (kind, data, bold, hic) in enumerate(cells):
            ty = yy - pad - fsize
            if kind == 'pill':
                pill(p, cx + pad, ty, data[0], data[1])
            else:
                for ln in data:
                    p.text(ln, cx + pad, ty, fsize,
                           hic or (INK if bold else BODY), bold)
                    ty -= fsize * 1.42
            cx += widths[i]
        yy -= rh
        p.rect(x, yy, total, 0.7, fill=LINE)
    return yy


def note(p, txt, x, y, maxw, dark=False):
    lines = wrap(txt, 8.5, maxw - 12)
    h = len(lines) * 12.0
    p.rect(x, y - h + 4, 2.5, h, fill=(0.35, 0.42, 0.52) if dark else LINE)
    yy = y
    for ln in lines:
        p.text(ln, x + 12, yy, 8.5, (0.65, 0.72, 0.79) if dark else MUTED)
        yy -= 12.0
    return yy


def label_bar(p, x, y, w, txt, col=TEAL, dark=False):
    bg = GREENBG if col == TEAL else (0.992, 0.957, 0.890)
    if dark:
        bg = (0.10, 0.26, 0.24) if col == TEAL else (0.24, 0.18, 0.06)
    p.rect(x, y - 21, w, 21, fill=bg, stroke=col, lw=0.7)
    p.text(txt.upper(), x + 11, y - 14, 8.2, col, True, char_space=1.1)
    return y - 21


PHOTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'team_photos')


def avatar(p, x, y, size, filename, initials, accent):
    """Jamoa a'zosi rasmi. y - yuqori chekka.

    team_photos/<filename> mavjud bo'lsa rasm qo'yiladi, aks holda ism-familiya
    bosh harflaridan o'rinbosar chiziladi. Deck rasmsiz ham to'g'ri ishlaydi.
    """
    ok = False
    for ext in ('', '.jpg', '.jpeg', '.JPG', '.JPEG'):
        cand = os.path.join(PHOTO_DIR, filename + ext) if ext else \
            os.path.join(PHOTO_DIR, filename)
        if os.path.exists(cand):
            ok = p.image(cand, x, y - size, size, size)
            if ok:
                break
    if not ok:
        p.rect(x, y - size, size, size, fill=(0.894, 0.925, 0.953))
        p.text_center(initials, x + size / 2.0, y - size / 2.0 - 6.5, 18,
                      (0.42, 0.51, 0.60), True)
    p.rect(x, y - size, size, 2.2, fill=accent)
    return ok


def dark_bg(p):
    p.rect(0, 0, W, H, fill=NAVY)
    p.rect(0, H - 4, W, 4, fill=TEAL)


# ─────────────────────────────────────────── Slaydlar

def build():
    pdf = PDF()

    # ═══ 01 Muqova ═══
    p = pdf.new_page()
    dark_bg(p)
    p.rect(ML, H - 142, 58, 4, fill=AMBER)
    p.text('PRE-SEED  ·  VALIDATSIYA VA PILOT BOSQICHI  ·  2026', ML, H - 120, 9,
           AMBER, True, char_space=1.5)
    p.text('SamCity', ML, H - 206, 58, WHITE, True)
    p.para('Kichik tumanlar uchun shahar xizmatlari platformasi.',
           ML, H - 248, 16, 760, (0.84, 0.90, 0.95), leading=23)
    p.text('Birinchi maqsad - Shofirkonda modelni isbotlash,', ML, H - 274, 16,
           AMBER, True)
    p.text('keyin boshqa tumanlarga ko’chirish.', ML, H - 297, 16,
           (0.84, 0.90, 0.95))
    bx = ML
    for lab in ['Mahsulot qurilgan', 'Bosqich: pilot oldi', 'So’rov: $15 000',
                'Yoshlar Ventures']:
        w = text_width(lab, 9.5, True) + 24
        p.rect(bx, 150, w, 26, fill=(0.13, 0.24, 0.38),
               stroke=(0.25, 0.36, 0.50), lw=0.8)
        p.text(lab, bx + 12, 159, 9.5, WHITE, True)
        bx += w + 10
    p.text('Hayitov Samandar - Founder  ·  4 kishilik jamoa  ·  '
           '+998 88 715 25 11  ·  @just_khayitov', ML, 118, 10, (0.62, 0.71, 0.80))
    band(p, 'Bu product-market fit da’vosi emas. Bu - tayyor mahsulotni bitta '
            'tumanda sinovdan o’tkazish taklifi.', 1, dark=True)

    # ═══ 02 Muammo ═══
    p = pdf.new_page()
    y = header(p, '01 · Muammo', 'Shofirkonda kundalik xizmatlar tizimsiz ishlaydi',
               'Bu bir marta uchraydigan muammo emas - har kuni, har xonadonda '
               'takrorlanadi. Aynan shuning uchun u biznes imkoniyati.')
    cw = (CW - 2 * 15) / 3.0
    cols = [
        ('Aholi zarar ko’radi',
         ['Taksi uchun qo’ng’iroq - narx oldindan noma’lum',
          'Do’konda katalog yo’q - nima bor, qancha turadi bilinmaydi',
          'To’yxona va salon broni og’zaki - chalkashadi',
          'Mahallaga murojaat - javob qachon kelishi noma’lum']),
        ('Mahalliy biznes zarar ko’radi',
         ['Yangi mijozga chiqishning yo’li yo’q',
          'Reklama = ko’chadagi banner yoki tanish orqali',
          'Buyurtmalar Telegramda tartibsiz - yo’qoladi',
          'Kim nima olganini bilmaydi - takroriy savdo yo’q']),
        ('Mahalla va hokimiyat zarar ko’radi',
         ['Aholiga xabar yetkazish kanali yo’q',
          'Murojaatlar qog’ozda, holati kuzatilmaydi',
          'Qaysi muammo qanchalik keng - o’lchanmaydi']),
    ]
    for i, (t, items) in enumerate(cols):
        x = ML + i * (cw + 15)
        p.rect(x, y - 132, cw, 132, fill=CARDBG, stroke=LINE, lw=0.8)
        p.rect(x, y - 132, 3, 132, fill=RED)
        p.text(t, x + 14, y - 19, 11.5, INK, True)
        bullets(p, items, x + 14, y - 40, 8.8, cw - 28, dot=RED, gap=4)
    y -= 146
    trio = [
        ('Nega bu muhim - takrorlanish',
         'Ovqat, mahsulot, transport, to’lov - haftada bir necha marta. Yuqori '
         'chastota = odat = barqaror biznes.'),
        ('Nega bu muhim - masshtab',
         'O’zbekistonda 200 dan ortiq tuman aynan shu holatda. Shofirkon - '
         'birinchi namuna, oxirgisi emas.'),
        ('Nega buni hech kim hal qilmaydi',
         'Yirik o’yinchilar uchun kichik tuman iqtisodiy jihatdan qiziq emas. '
         'Mahalliy o’yinchida esa texnologiya yo’q.'),
    ]
    for i, (t, b) in enumerate(trio):
        card(p, ML + i * (cw + 15), y, cw, 72, t, b, tsize=10.5, bsize=8.6)
    band(p, 'Muammo real, kundalik va takrorlanadigan - va uni hal qilishga '
            'hozircha na yirik, na mahalliy o’yinchi kirmoqda.', 2)

    # ═══ 03 Yechim ═══
    p = pdf.new_page()
    y = header(p, '02 · Yechim', 'Har bir muammo uchun bitta aniq yechim',
               'Sodda til bilan: SamCity tumandagi barcha xizmatlarni bitta ilovaga '
               'yig’adi va ularni ko’rinadigan, o’lchanadigan qiladi.')
    widths = [CW * 0.34, CW * 0.46, CW * 0.20]
    rows = [
        ['Taksi chaqirish uchun qo’ng’iroq, narx noma’lum',
         '**Ilovadan taksi chaqirasiz. Narx oldindan ko’rinadi, mashina xaritada, '
         'haydovchining bahosi bor', 'Yo’lovchi + haydovchi'],
        ['Do’konda katalog yo’q, buyurtma Telegramda',
         '**Do’konning mahsulotlari narxi bilan ko’rinadi. Savatga solasiz, '
         'buyurtma beriladi, yetkazilishi kuzatiladi', 'Xaridor + do’kon'],
        ['Bron og’zaki - ikki marta bron, kelmay qolish',
         '**Bo’sh vaqtni ko’rib bron qilasiz. Oldindan to’lov bor - kelmay '
         'qolish kamayadi', 'Mijoz + joy egasi'],
        ['Mahallaga murojaat - javob qachon kelishi noma’lum',
         '**Murojaat holati ko’rinadi: yuborildi -> ko’rilmoqda -> hal qilindi. '
         'Rais va hokim panelidan javob beradi', 'Fuqaro + mahalla'],
        ['Biznes reklama qila olmaydi',
         '**O’z mahallasidagi odamlarga xabar yuboradi. Kim ko’rgani va kim '
         'buyurtma berganini ko’radi', 'Mahalliy biznes'],
    ]
    y = table(p, ML, y, widths,
              ['Bugungi holat', 'SamCity nima qiladi', 'Kim yutadi'], rows,
              fsize=8.2, pad=5.5)
    y -= 14
    p.text('Va ularni bir-biriga bog’laydigan to’rtta qatlam:', ML, y, 9.5,
           INK, True)
    y -= 12
    cw4 = (CW - 3 * 13) / 4.0
    layers = [
        ('Yagona qidiruv',
         'Bitta qidiruv oynasi: do’kon, mahsulot, joy, e’lon, ish o’rni. '
         'Foydalanuvchi nima izlayotganini aniq bilmasa ham topadi.', TEAL),
        ('Xarita',
         '16 toifadagi joy - dorixona, shifoxona, bank, maktab. Masofa, piyoda '
         'vaqti, ochiq/yopiq holati va yo’nalish bilan.', TEAL),
        ('Mahalla',
         'Rais e’lonlari, murojaat kuzatuvi, so’rovnoma, yordam markazi. Boshqa '
         'hech qayerda yo’q - bizning tarqatish kanalimiz.', TEAL),
        ('AI yordamchi',
         'O’zbek tilida savol berasiz: "eng yaqin ochiq dorixona qayerda?" Javob '
         'masofa, piyoda vaqti va yo’nalish bilan - ovozli ham.', AMBER),
    ]
    for i, (t, b, acc) in enumerate(layers):
        card(p, ML + i * (cw4 + 13), y, cw4, 84, t, b, accent=acc, tsize=10.5,
             bsize=8.2)
    y -= 96
    note(p, 'AI yordamchi bugun javob beradi. Keyingi bosqich - amalni ham bajarsin: '
            '"taksi chaqir", "non buyurtma qil". Ovoz bilan boshqariladigan shahar '
            'yordamchisi - bu bizning uzoq muddatli farqimiz.', ML, y, CW)
    band(p, 'Yechim mavhum emas: har bir muammoga bitta aniq funksiya to’g’ri '
            'keladi va ularning hammasi allaqachon yozilgan.', 3)

    # ═══ 04 Nega odamlar ═══
    p = pdf.new_page()
    y = header(p, '03 · Foydalanuvchi',
               'Nega odam Telegram o’rniga SamCity’ni ochadi',
               'Bu deck’dagi eng muhim savol. Bizning haqiqiy raqibimiz Yandex '
               'emas - bepul Telegram va telefon qo’ng’irog’i.')
    hw = (CW - 44) / 2.0
    p.rect(ML, y - 140, hw, 140, fill=REDBG)
    p.text('TELEGRAM / QO’NG’IROQ BILAN', ML + 16, y - 20, 8.5,
           (0.651, 0.196, 0.184), True, char_space=1.1)
    bullets(p, ['Har do’kon - alohida kanal. Qaysi birida bor, izlash kerak',
                'Narx yozilmagan yoki eskirgan - so’rash kerak',
                'Buyurtma xabarlar orasida yo’qoladi',
                'Kim yetkazayotgani va qachon kelishi noma’lum',
                'Sifat kafolati yo’q - shikoyat qiladigan joy yo’q',
                'Narx solishtirib bo’lmaydi'],
            ML + 16, y - 40, 8.8, hw - 32, dot=(0.80, 0.45, 0.45), gap=3)
    mx = ML + hw
    p.rect(mx, y - 140, 44, 140, fill=NAVY)
    p.text_center('->', mx + 22, y - 76, 15, WHITE, True)
    x2 = mx + 44
    p.rect(x2, y - 140, hw, 140, fill=GREENBG)
    p.text('SAMCITY BILAN', x2 + 16, y - 20, 8.5, (0.075, 0.455, 0.271), True,
           char_space=1.1)
    bullets(p, ['**Hamma do’kon bitta ro’yxatda - qidiruv bilan topiladi',
                '**Narx har doim ko’rinadi va solishtiriladi',
                '**Buyurtma tarixi saqlanadi - nima olganingiz yozilgan',
                '**Yetkazuvchi xaritada - qachon kelishi ko’rinadi',
                '**Baho va sharh - kimga ishonish mumkinligi bilinadi',
                '**Mahalla xabarlari ham shu yerda - boshqa joyda yo’q'],
            x2 + 16, y - 40, 8.8, hw - 32, dot=GREEN, gap=3)
    y -= 154
    cw4 = (CW - 3 * 13) / 4.0
    for i, (t, b) in enumerate([
        ('Kunlik sabab', 'Oziq-ovqat va mahsulot buyurtmasi - eng tez-tez '
                         'takrorlanadigan ehtiyoj.'),
        ('Haftalik sabab', 'Taksi, dorixona, bron - muntazam, lekin har kun emas.'),
        ('Oylik sabab', 'Kommunal, kurs va bog’cha to’lovi - qaytarib '
                        'bo’lmaydigan odat.'),
        ('Doimiy sabab', 'Mahalla e’lonlari va murojaat - faqat bizda bor, '
                         'alternativasi yo’q.')]):
        card(p, ML + i * (cw4 + 13), y, cw4, 66, t, b, accent=TEAL, tsize=10.5,
             bsize=8.4)
    y -= 78
    note(p, 'Halol chegara: biz odamlar Telegramdan voz kechadi demaymiz. Biz '
            'do’kon topish, narx solishtirish va buyurtmani kuzatish uchun '
            'kelishini kutamiz. Aynan shu farazni pilotda tekshiramiz.', ML, y, CW)
    band(p, 'Biz raqibni to’g’ri aniqlaganmiz va foydalanuvchi uchun aniq, '
            'o’lchanadigan afzallik taklif qilamiz - shior emas.', 4)

    # ═══ 05 Nega bizneslar ═══
    p = pdf.new_page()
    y = header(p, '04 · Biznes tomoni',
               'Nega do’kon qo’shiladi - va nega keyin to’laydi',
               'Marketplace’da eng qiyin tomon - supply. Shuning uchun biznes uchun '
               'qiymat birinchi kundan aniq bo’lishi kerak.')
    hw = (CW - 22) / 2.0
    ly = label_bar(p, ML, y, hw, 'Nega qo’shiladi - birinchi 3 oy bepul', TEAL)
    bullets(p, ['**Yangi mijoz oqimi. Do’kon o’z mahallasidan tashqaridagi '
                'xaridorlarga ko’rinadi - bugun bu imkoniyat yo’q',
                '**Tayyor raqamli vitrina. Katalogda mahsulotlar rasmi va nomi '
                'bilan turibdi - do’kon nol ish qiladi',
                '**Buyurtmalar bir joyda. Telegram xabarlari o’rniga tartibli '
                'ro’yxat, holati bilan',
                '**Obunachilarga xabar. Kanal qurish shart emas - "yangi mahsulot '
                'keldi" xabari mijozga boradi',
                '**Onboarding’ni biz qilamiz. Katalogni biz kiritamiz, rasmini '
                'biz olamiz'],
            ML, ly - 14, 9.0, hw, gap=5)

    rx = ML + hw + 22
    ry = label_bar(p, rx, y, hw, 'Nega 3 oydan keyin to’laydi', AMBER)
    ry -= 14
    p.rect(rx, ry - 132, hw, 132, fill=CARDBG, stroke=LINE, lw=0.8)
    p.rect(rx, ry - 132, 3, 132, fill=AMBER)
    p.text('To’lov mantig’i juda sodda', rx + 14, ry - 19, 11.5, INK, True)
    p.para('Obuna - oyiga 100 000 so’m. O’rtacha chek 25 000 so’m, '
           'do’konning marjasi ~20% = 5 000 so’m.',
           rx + 14, ry - 38, 9.0, hw - 28, BODY, leading=13)
    p.rect(rx + 14, ry - 96, hw - 28, 34, fill=WHITE, stroke=LINE, lw=0.8)
    p.text('Obuna o’zini qoplashi uchun kerak:', rx + 24, ry - 74, 8.8, BODY)
    p.text('oyiga 20 ta qo’shimcha buyurtma - kuniga bittadan kam.',
           rx + 24, ry - 88, 9.2, TEAL, True)
    p.para('Agar biz shuni bera olmasak, do’kon to’lamaydi va to’lamasligi '
           'ham kerak. Pilotning asosiy tekshiruvi - aynan shu.',
           rx + 14, ry - 108, 8.6, hw - 28, MUTED, leading=12)
    card(p, rx, ry - 142, hw, 54, 'Bosqichma-bosqich narx',
         '1-3 oy bepul -> 4-oydan obuna. Do’kon qiymatni ko’rgandan keyin '
         'to’laydi, va’daga emas.', accent=TEAL, tsize=10.5, bsize=8.6)
    band(p, 'Bizda supply’ni jalb qilishning aniq mantig’i bor va obuna narxi '
            'do’konning foydasiga bog’langan - havodan olinmagan.', 5)

    # ═══ 06 Biznes model ═══
    p = pdf.new_page()
    y = header(p, '05 · Biznes model', 'Daromad beshta manbadan keladi',
               'Ikkitasi bugun texnik jihatdan tayyor, uchtasi pilot davomida '
               'yoqiladi. Hech biri hali real pul keltirmagan - buni ochiq aytamiz.')
    widths = [CW * 0.22, CW * 0.17, CW * 0.18, CW * 0.28, CW * 0.15]
    rows = [
        ['**Biznes obunasi', 'Do’kon, kafe, salon', '100 000 so’m / oy',
         'Doimiy mijoz oqimi va raqamli vitrina', ('Pilotda', 'pill', 'mid')],
        ['**Yetkazib berish komissiyasi', 'Do’kon', 'Buyurtmadan 8%',
         'Yangi buyurtma - o’z mijozidan emas, bizdan kelgan',
         ('Pilotda', 'pill', 'mid')],
        ['**Taksi komissiyasi', 'Haydovchi / xizmat', 'Safardan 5-7%',
         'Bo’sh vaqtda qo’shimcha buyurtma oqimi', ('Pilotda', 'pill', 'mid')],
        ['**Reklama', 'Mahalliy biznes', 'Kampaniya bo’yicha',
         'Aniq mahalla va yosh guruhiga xabar yuborish', ('Tayyor', 'pill', 'ok')],
        ['**Premium listing', 'Do’kon, taksist, joy', 'Oylik to’lov',
         'Ro’yxatda yuqorida turish - ko’proq ko’rinish',
         ('Tayyor', 'pill', 'ok')],
    ]
    y = table(p, ML, y, widths,
              ['Daromad manbai', 'Kim to’laydi', 'Qancha', 'Nima uchun to’laydi',
               'Holati'], rows, fsize=8.4, pad=6)
    y -= 16
    cw3 = (CW - 2 * 15) / 3.0
    for i, (t, b, acc) in enumerate([
        ('Pilot bosqichida (0-12 oy)', 'Asosiy e’tibor obuna va yetkazib berish '
         'komissiyasiga. Maqsad - daromad hajmi emas, to’lovga tayyorlikni '
         'isbotlash.', TEAL),
        ('Kengayish bosqichida', 'Komissiya asosiy oqimga aylanadi - u har bir yangi '
         'tumanda avtomatik takrorlanadi.', TEAL),
        ('Halol ogohlantirish', 'Bu narxlarning hech biri hali bozorda '
         'tekshirilmagan. Pilotning birinchi vazifasi - haqiqiy narxni topish.',
         AMBER)]):
        card(p, ML + i * (cw3 + 15), y, cw3, 74, t, b, accent=acc, tsize=10.5,
             bsize=8.6)
    band(p, 'Daromad modeli tushunarli va takrorlanadigan, lekin biz uni '
            'isbotlangan deb ko’rsatmayapmiz - bu pilotning maqsadi.', 6)

    # ═══ 07 Hozirgi holat ═══
    p = pdf.new_page()
    dark_bg(p)
    y = header(p, '06 · Hozirgi holat', 'Nima qurilgan va nima hali isbotlanmagan',
               'Bu slaydda hech narsani bo’lmaymiz. Investor baribir bilib oladi - '
               'o’zimiz aytganimiz kuchliroq.', dark=True)
    hw = (CW - 20) / 2.0
    p.rect(ML, y - 152, hw, 152, fill=(0.09, 0.24, 0.18),
           stroke=(0.20, 0.45, 0.32), lw=0.9)
    p.rect(ML, y - 152, 3, 152, fill=GREEN)
    p.text('QURILGAN VA ISHLAYDI', ML + 16, y - 20, 10, (0.37, 0.84, 0.60), True,
           char_space=1.0)
    bullets(p, ['**Yetkazib berish - do’kon, katalog, savat, buyurtma, kuryer',
                '**Taksi - haydovchi, marshrut, safar, jonli kuzatuv',
                '**Bron - joy, xizmat, usta, vaqt tanlash, oldindan to’lov',
                '**Mahalla - rais va hokim paneli, murojaat, so’rovnoma',
                '**To’lov - Payme va Click ulanishi yozilgan',
                '**Ikkala platforma - veb sayt va mobil ilova'],
            ML + 16, y - 42, 8.8, hw - 32, dark=True, dot=GREEN, gap=4)
    x2 = ML + hw + 20
    p.rect(x2, y - 152, hw, 152, fill=(0.26, 0.12, 0.12),
           stroke=(0.50, 0.24, 0.24), lw=0.9)
    p.rect(x2, y - 152, 3, 152, fill=RED)
    p.text('HALI ISBOTLANMAGAN', x2 + 16, y - 20, 10, (1.0, 0.56, 0.55), True,
           char_space=1.0)
    bullets(p, ['**Foydalanuvchi yo’q - real foydalanuvchi bazasi yig’ilmagan',
                '**Daromad yo’q - birorta ham real tranzaksiya o’tmagan',
                '**Hech kim to’lashga rozi bo’lmagan - obuna narxi sinalmagan',
                '**Supply yig’ish sinalmagan - onboarding tekshirilmagan',
                '**Retention noma’lum - odamlar qaytib keladimi, bilmaymiz'],
            x2 + 16, y - 42, 8.8, hw - 32, dark=True, dot=RED, gap=4)
    y -= 166
    cw3 = (CW - 2 * 15) / 3.0
    for i, (t, b) in enumerate([
        ('Bosqichimiz nomi', 'Pilot oldi. Mahsulot bosqichidan chiqdik, bozor '
                             'bosqichiga hali kirmadik.'),
        ('Nega bu yaxshi xabar', 'Ko’p startap bu bosqichga yetish uchun 12 oy va '
                                 'katta byudjet sarflaydi. Biz uni o’tganmiz.'),
        ('Nega bu risk', 'Qurilgan mahsulot - bozor bor degani emas. Aynan shu '
                         'noaniqlikni yopish uchun kelganmiz.')]):
        card(p, ML + i * (cw3 + 15), y, cw3, 70, t, b, dark=True, tsize=10.5,
             bsize=8.6)
    band(p, 'Founder o’z holatini xolis baholaydi va traksiya yo’qligini '
            'yashirmaydi - bu ishonchli hamkorlikning birinchi sharti.', 7, dark=True)

    # ═══ 08 Jamoa ═══
    p = pdf.new_page()
    y = header(p, '07 · Jamoa', 'Loyihani kim quradi',
               'To’rt kishilik jamoa - barchamiz Shofirkon bilan bog’liqmiz.')
    cw4 = (CW - 3 * 13) / 4.0
    team = [
        ('Hayitov Samandar', 'FOUNDER & PROJECT MANAGER  ·  17 YOSH',
         'Backend va frontend dasturchi. Loyiha asoschisi - arxitektura va '
         'asosiy kod uning qo’lida.', AMBER, 'samandar', 'HS',
         '@just_khayitov', 'just_khayitovv', '+998 88 715 25 11'),
        ('Abrorbek', 'PROJECT MANAGER  ·  28 YOSH',
         'Flutter mutaxassisi. Shofirkondagi IT markazda dasturlashdan dars '
         'beradi - mahalliy jamiyatda tayyor tarmoq.', TEAL, 'abror', 'A',
         None, None, '+998 50 087 64 02'),
        ('Beknazarov Bekzod', 'DASTURCHI  ·  17 YOSH',
         'Frontend dasturchi. Ilgari 2 ta startap qurgan; ulardan biri 1 000 dan '
         'ortiq foydalanuvchi jalb qilgan.', TEAL, 'bekzod', 'BB',
         '@beknazarovbehzod', 'beknzarov', '+998 93 454 83 16'),
        ('G’ulomov Ozodbek', 'MARKETOLOG  ·  20 YOSH',
         'SMM mutaxassisi. Foydalanuvchi jalb qilish va mahalliy marketing uchun '
         'javobgar.', TEAL, 'ozodbek', 'GO',
         '@just_ozodbek', 'just_ozodbek', '+998 97 369 80 81'),
    ]
    CH = 206.0
    for i, (name, role, desc, acc, photo, ini, tg, ig, tel) in enumerate(team):
        x = ML + i * (cw4 + 13)
        iw = cw4 - 28
        p.rect(x, y - CH, cw4, CH, fill=CARDBG, stroke=LINE, lw=0.8)
        p.rect(x, y - CH, 3, CH, fill=acc)
        avatar(p, x + 14, y - 12, 54, photo, ini, acc)
        p.text(name, x + 14, y - 84, 11.5, INK, True)
        p.para(role, x + 14, y - 97, 7.2, iw, MUTED, True, leading=9.5)
        cy = y - 116
        if tg:
            p.text(tg, x + 14, cy, 8.0, acc, True)
            cy -= 11.5
        if ig:
            p.text('insta: ' + ig, x + 14, cy, 7.6, MUTED)
            cy -= 11.5
        p.text(tel, x + 14, cy, 8.0, BODY, True)
        p.rect(x + 14, y - 156, iw, 0.7, fill=LINE)
        p.para(desc, x + 14, y - 168, 8.0, iw, BODY, leading=11)
    y -= CH + 12
    cw3 = (CW - 2 * 15) / 3.0
    for i, (t, b) in enumerate([
        ('Mahalliy jamoa', 'Do’kon egalari va mahalla faollari bilan aloqa - begona '
                           'uchun eng qiyin qism, biz uchun kundalik holat.'),
        ('To’liq qamrov', 'Backend, mobil, frontend va marketing - to’rttasi ham '
                          'ichkarida. Tashqaridan yollash shart emas.'),
        ('Startap tajribasi', 'Jamoada 1 000+ foydalanuvchi jalb qilgan a’zo bor - '
                              'foydalanuvchi yig’ish nazariya emas.')]):
        card(p, ML + i * (cw3 + 15), y, cw3, 56, t, b, accent=TEAL, tsize=10,
             bsize=8.0)
    y -= 66
    note(p, 'Ochiq aytamiz: jamoa yosh va bizda savdo hamda operatsion boshqaruv '
            'tajribasi yetishmaydi. Aynan shu yo’nalishda mentorlik so’raymiz - '
            '11-slaydga qarang.', ML, y, CW)
    band(p, 'Jamoa to’liq va mahalliy: mahsulotni qurish ham, birinchi mijozlarni '
            'yig’ish ham ichki kuch bilan bajariladi.')

    # ═══ 09 12 oylik reja ═══
    p = pdf.new_page()
    y = header(p, '08 · Keyingi 12 oy', 'Uch bosqich, har birida o’lchanadigan maqsad',
               'Reja "ishlaymiz" degan so’zdan iborat emas - har bosqichning chiqish '
               'mezoni bor.')
    cw3 = (CW - 2 * 18) / 3.0
    phases = [
        (TEAL, '0-3 OY · ISHGA TUSHIRISH', 'Shofirkonda start',
         ['SMS va to’lov ulanishi jonlashtiriladi',
          'Ilova Play Market’ga chiqariladi',
          '**30-40 do’kon va biznes ulanadi',
          '**3-5 mahalla raisi bilan kelishuv',
          '3-5 kuryer va 10+ taksist jalb qilinadi'],
         'Chiqish mezoni: 500 ro’yxatdan o’tgan foydalanuvchi, kuniga 10+ real '
         'buyurtma'),
        (AMBER, '3-6 OY · ISBOTLASH', 'Model ishlaydimi?',
         ['Komissiya va obuna to’lovi yoqiladi',
          '**Birinchi to’lovchi bizneslar - kamida 10 ta',
          'Retention o’lchanadi: D7 va D30',
          'Qaysi modul ishlayotgani aniqlanadi',
          'Yetkazib berish jarayoni sozlanadi'],
         'Chiqish mezoni: 1 500 foydalanuvchi, D30 >= 20%, birinchi real daromad'),
        (NAVY2, '6-12 OY · KO’CHIRISH', 'Takrorlanadimi?',
         ['Shofirkon natijalari hujjatlashtiriladi',
          '**Ikkinchi tumanga kirish (mezonlar bajarilsa)',
          'Birinchi tumanni xarajat qoplash darajasiga chiqarish',
          'Keyingi raund uchun real raqamli deck'],
         'Chiqish mezoni: 2 tumanda faoliyat, takrorlanadigan onboarding modeli'),
    ]
    for i, (col, when, title, items, res) in enumerate(phases):
        x = ML + i * (cw3 + 18)
        p.rect(x, y - 4, cw3, 4, fill=col)
        p.text(when, x, y - 21, 8.2, MUTED, True, char_space=1.1)
        p.text(title, x, y - 42, 14.5, INK, True)
        by = bullets(p, items, x, y - 64, 8.8, cw3, gap=4, dot=col)
        bg = HEADBG if col == TEAL else ((0.992, 0.969, 0.918) if col == AMBER
                                         else (0.933, 0.953, 0.976))
        p.rect(x, by - 40, cw3, 40, fill=bg)
        p.para(res, x + 10, by - 15, 8.6, cw3 - 20, INK, True, leading=11.5)
    note(p, 'Muhim shart: agar 3-6 oyda bizneslar to’lashdan bosh tortsa yoki '
            'retention past bo’lsa - biz ikkinchi tumanga kengaymaymiz. Model '
            'tuzatiladi yoki o’zgartiriladi. Kengayish avtomatik emas, mezonga '
            'bog’liq.', ML, FLOOR + 26, CW)
    band(p, 'Reja mezonlarga bog’langan - founder yomon natijani ko’rsa '
            'to’xtashga tayyor, bu kapitalni tejaydi.', 8)

    # ═══ 09 Nega investitsiya ═══
    p = pdf.new_page()
    dark_bg(p)
    y = header(p, '09 · Nega investitsiya kerak', 'Pul mahsulot uchun emas - bozor uchun',
               'Bu deck’dagi eng muhim ajratish. Ko’p startap kapitalni qurish '
               'uchun so’raydi; bizda qurilgan qism allaqachon tugagan.', dark=True)
    hw = (CW - 22) / 2.0
    p.rect(ML, y - 148, hw, 148, fill=(0.11, 0.17, 0.25),
           stroke=(0.22, 0.28, 0.36), lw=0.9)
    p.text('INVESTITSIYA BUNGA KETMAYDI', ML + 16, y - 20, 9.5,
           (0.55, 0.62, 0.70), True, char_space=1.0)
    yy = y - 44
    for lab in ['Mahsulot qurish - tugallangan',
                'Dizayn va arxitektura - tugallangan',
                'To’lov integratsiyasi - yozilgan',
                'Mobil ilova - yozilgan']:
        p.rect(ML + 16, yy - 1.5, 5.0, 5.0, fill=(0.42, 0.48, 0.55))
        p.text(lab, ML + 31, yy, 9.2, (0.60, 0.67, 0.74))
        yy -= 20
    p.para('Bu bosqich jamoa tomonidan tashqi kapitalsiz bosib o’tilgan.',
           ML + 16, yy - 6, 8.8, hw - 32, (0.52, 0.60, 0.68), leading=12)

    x2 = ML + hw + 22
    p.rect(x2, y - 148, hw, 148, fill=(0.24, 0.18, 0.06), stroke=AMBER, lw=1.0)
    p.rect(x2, y - 148, 3, 148, fill=AMBER)
    p.text('INVESTITSIYA AYNAN BUNGA KETADI', x2 + 16, y - 20, 9.5, AMBER, True,
           char_space=1.0)
    bullets(p, ['**Foydalanuvchi yig’ish - birinchi 1 500 odamni ilovaga olib kelish',
                '**Bizneslarni ulash - 40 do’konni onboard qilish, katalogini kiritish',
                '**Yetkazib berish infratuzilmasi - kuryerlar, ish haqi va jihoz',
                '**Marketing - mahalla kanallari, flayer, birinchi buyurtma rag’bati',
                '**Pilotni tezlashtirish - 12 oyda emas, 6 oyda javob olish'],
            x2 + 16, y - 42, 8.8, hw - 32, dark=True, dot=AMBER, gap=4)
    y -= 162
    p.rect(ML, y - 56, CW, 56, fill=(0.13, 0.24, 0.38),
           stroke=(0.25, 0.36, 0.50), lw=0.8)
    p.text('Boshqacha aytganda:', ML + 18, y - 22, 11.5, WHITE, True)
    p.text('siz mahsulot qurilishiga emas, tayyor mahsulotning bozorda ishlashini '
           'tekshirishga investitsiya qilasiz.',
           ML + 18 + text_width('Boshqacha aytganda: ', 11.5, True), y - 22, 11.5,
           AMBER, True)
    p.text('Bu - startap hayotidagi eng arzon va eng aniq javob olinadigan bosqich.',
           ML + 18, y - 42, 10, (0.78, 0.85, 0.91))
    band(p, 'Kapital texnik riskka emas, bozor riskiga yo’naltiriladi - va bu '
            'riskning javobi 6 oyda ma’lum bo’ladi.', 9, dark=True)

    # ═══ 10 $15 000 rejasi ═══
    p = pdf.new_page()
    y = header(p, '10 · Mablag’dan foydalanish',
               '$15 000 - har bir dollarning natijasi bilan',
               'Bu xarajatlar ro’yxati emas. Har bir yo’nalish yonida u nima '
               'keltirishi kerakligi yozilgan.')
    widths = [CW * 0.25, CW * 0.11, CW * 0.35, CW * 0.29]
    rows = [
        ['**Marketing va foydalanuvchi yig’ish', '$$$5 000',
         'Mahalla kanallari, flayer va QR, birinchi buyurtma rag’bati, lokal '
         'Telegram reklama',
         '**1 500 ro’yxatdan o’tgan; 500+ haftalik faol foydalanuvchi'],
        ['**Yetkazib berish infratuzilmasi', '$$$2 500',
         '3-5 kuryer bilan ishlash, ularning to’lovi, sumka va jihoz, marshrut '
         'sinovlari',
         '**Kuniga 30+ buyurtma quvvati; yetkazish < 45 daqiqa'],
        ['**Biznes onboarding', '$$$2 000',
         'Do’konlarga borish, katalogni kiritish, mahsulot rasmini olish, '
         'o’qitish',
         '**40 biznes ulangan; 10+ to’lovchi obunachi (4-oydan)'],
        ['**Server va infratuzilma', '$$$1 500',
         'Server, domen, SMS paketi, to’lov shlyuzi ulanishi, Play Market hisobi',
         '**12 oy uzluksiz ishlash; ilova do’konda mavjud'],
        ['**Jamoa stipendiyasi', '$$$2 000',
         'Jamoa boshqa ishga chalg’imasdan pilotga to’liq vaqt ajratishi',
         '**Asosiy vaqt loyihaga; pilot 12 oy o’rniga 6 oyda'],
        ['**Zaxira fondi', '$$$2 000',
         'Kutilmagan xarajat, pilot muddatini uzaytirish, model o’zgarsa qayta '
         'sinov', '**Rejadan chetga chiqilsa to’xtab qolmaslik'],
        ['**JAMI', '**$15 000', '**12 oylik pilot dasturi',
         '**Shofirkonda model ishlaydimi - aniq javob'],
    ]
    y = table(p, ML, y, widths,
              ['Yo’nalish', 'Summa', 'Nimaga sarflanadi',
               'Kutilayotgan natija (KPI)'], rows, fsize=8.2, pad=5.5)
    y -= 14
    note(p, 'Har chorakda investorga hisobot: sarflangan mablag’, erishilgan KPI va '
            'keyingi chorak rejasi. Mezon bajarilmasa - sabab va tuzatish rejasi '
            'bilan.', ML, y, CW)
    band(p, 'Har bir dollar aniq natijaga bog’langan va hisobot tartibi oldindan '
            'belgilangan - pul qayerga ketgani ko’rinib turadi.', 10)

    # ═══ 11 Yordam ═══
    p = pdf.new_page()
    y = header(p, '11 · Yordam', 'Bizga puldan tashqari nima kerak',
               'Ochig’ini aytamiz: ba’zi yo’nalishlarda pul emas, eshik ochish '
               'ko’proq qiymat beradi.')
    cw3 = (CW - 2 * 15) / 3.0
    helps = [
        ('Mentorlik', 'Jamoa texnik va marketing tomonda kuchli, lekin savdo hamda '
                      'operatsion boshqaruvda tajribasi kam. Marketplace birlik '
                      'iqtisodiyoti bo’yicha maslahat - eng katta bo’shliqni '
                      'yopadi.', TEAL),
        ('Mahalliy bizneslarga kirish', 'Birinchi 20-30 do’kon eng qiyini. '
                                        'Tanishtiruv orqali kirish bu jarayonni '
                                        'oylardan haftalarga qisqartiradi.', TEAL),
        ('Hamkorliklar va pilot', 'Mahalla va tuman darajasidagi rasmiy '
                                  'qo’llab-quvvatlash - eng arzon va eng ishonchli '
                                  'tarqatish kanalimizni ochadi.', TEAL),
        ('PR va media', '"Birinchi raqamli tuman" hikoyasi bepul foydalanuvchi jalb '
                        'qiladi va keyingi tumanlarga kirishda ishonch yaratadi.', TEAL),
        ('Keyingi investorlar', 'Pilot natijalari chiqqach, seed bosqichidagi '
                                'investorlar bilan tanishtirish - 12 oylik '
                                'maqsadimiz.', TEAL),
        ('Huquqiy va moliyaviy', 'To’lov agenti maqomi, soliq va shartnoma '
                                 'tuzilmasi bo’yicha yo’l-yo’riq - kichik '
                                 'jamoada bu eng ko’p vaqt oladigan qism.', AMBER),
    ]
    for i, (t, b, acc) in enumerate(helps):
        col, row = i % 3, i // 3
        card(p, ML + col * (cw3 + 15), y - row * 108, cw3, 96, t, b, accent=acc,
             tsize=11.5, bsize=8.8)
    y -= 216
    note(p, 'Loyiha investitsiyasiz ham davom etadi. Ammo yuqoridagi yordam tezlikni '
            'bir necha barobar oshiradi - va bu bozorda tezlik asosiy himoya '
            'vositasi.', ML, y, CW)
    band(p, 'Founder o’z kuchsiz tomonlarini biladi va yordamni aniq nuqtalarda '
            'so’raydi - bu boshqarish oson hamkorlik degani.', 11)

    # ═══ 12 Yakuniy ═══
    p = pdf.new_page()
    dark_bg(p)
    p.text('12 · YAKUNIY FIKR', ML, H - MT - 8, 8.5, AMBER, True, char_space=1.5)
    y = H - 108
    p.text('Biz investitsiyani ', ML, y, 22, WHITE, True)
    x1 = ML + text_width('Biz investitsiyani ', 22, True)
    p.text('mahsulot qurish', x1, y, 22, (0.55, 0.63, 0.71), True)
    p.text(' uchun emas,', x1 + text_width('mahsulot qurish', 22, True), y, 22,
           WHITE, True)
    y -= 32
    p.text('Shofirkonda modelni isbotlash', ML, y, 22, AMBER, True)
    p.text(' uchun qidirmoqdamiz.',
           ML + text_width('Shofirkonda modelni isbotlash', 22, True), y, 22,
           WHITE, True)
    y -= 40
    p.text('Agar model ishlasa - uni ', ML, y, 18, (0.80, 0.87, 0.93))
    p.text('200 dan ortiq tumanga', ML + text_width('Agar model ishlasa - uni ', 18),
           y, 18, AMBER, True)
    p.text(' ko’chirish mumkin bo’ladi.',
           ML + text_width('Agar model ishlasa - uni ', 18)
           + text_width('200 dan ortiq tumanga', 18, True), y, 18,
           (0.80, 0.87, 0.93))
    y -= 34
    cw3 = (CW - 2 * 15) / 3.0
    for i, (t, b, acc) in enumerate([
        ('Nima tayyor', 'To’liq ishlaydigan mahsulot - veb va mobil, to’lov va '
                        'xarita bilan. Bu bosqich kapitalsiz bosib o’tilgan.', GREEN),
        ('Nima tekshiriladi', 'Odamlar foydalanadimi, bizneslar to’laydimi, model '
                              'bitta tumanda o’zini qoplaydimi.', AMBER),
        ('Nima so’ralmoqda', '$15 000 + mentorlik + mahalliy bizneslarga va '
                                'hokimiyatga kirish.', TEAL)]):
        card(p, ML + i * (cw3 + 15), y, cw3, 84, t, b, accent=acc, dark=True,
             tsize=11.5, bsize=8.8)
    y -= 100
    p.rect(ML, y, CW, 0.8, fill=(0.30, 0.38, 0.48))
    y -= 26
    p.text('Hayitov Samandar', ML, y, 20, WHITE, True)
    p.text('FOUNDER · SAMCITY  ·  4 KISHILIK JAMOA', ML, y - 17, 8.5, AMBER, True,
           char_space=1.3)
    bx = ML + CW * 0.44
    p.rect(bx, y - 30, CW - (bx - ML), 56, fill=(0.24, 0.18, 0.06),
           stroke=AMBER, lw=1.0)
    p.text('+998 88 715 25 11  ·  @just_khayitov  ·  insta: just_khayitovv',
           bx + 16, y + 8, 10, WHITE)
    p.text('Jonli demo tayyor - 10 daqiqada butun mahsulotni ko’rsataman.',
           bx + 16, y - 10, 9.2, AMBER)
    band(p, 'Bu past xarajatli, aniq muddatli va aniq javobli tajriba - natijasi '
            '6-12 oyda ma’lum bo’ladi.', 12, dark=True)

    return pdf


SLIDE_NAMES = [
    'Muqova', 'Muammo', 'Yechim', 'Nega odamlar foydalanadi',
    'Nega bizneslar qo’shiladi', 'Biznes model', 'Hozirgi holat',
    'JAMOA', 'Keyingi 12 oy', 'Nega investitsiya kerak',
    '$15 000 rejasi', 'Qanday yordam kerak', 'Yakuniy fikr',
]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, 'SamCity_Investor_Deck.pdf')

    pdf = build()
    try:
        pdf.save(out)
    except PermissionError:
        # Eng ko'p uchraydigan xato: PDF hozir ochiq turibdi va Windows
        # faylni qulflab qo'ygan. Eski faylni o'zgartirib bo'lmaydi.
        print('')
        print('  XATO: PDF fayl hozir ochiq turibdi!')
        print('')
        print('  SamCity_Investor_Deck.pdf ni YOPING (brauzer yoki PDF')
        print('  dasturida ochiq bo\'lishi mumkin), so\'ng shu faylni')
        print('  qayta ishga tushiring.')
        print('')
        print('  Aks holda eski, yangilanmagan PDF qolib ketadi.')
        print('')
        return

    n = len(pdf.pages)
    print('')
    print('  TAYYOR!')
    print('  Fayl:   %s' % out)
    print('  Hajmi:  %.0f KB  |  %d slayd  |  960x540 pt (16:9)'
          % (os.path.getsize(out) / 1024.0, n))
    print('')
    print('  Slaydlar:')
    for i, nm in enumerate(SLIDE_NAMES[:n], start=1):
        mark = '  <-- rasm qo\'yiladigan joy' if nm == 'JAMOA' else ''
        print('    %2d. %s%s' % (i, nm, mark))
    print('')

    # Rasm holati - qaysi jamoa rasmi topildi, qaysi biri yo'q
    missing = []
    for fn, who in (('samandar', 'Hayitov Samandar'), ('abror', 'Abrorbek'),
                    ('bekzod', 'Beknazarov Bekzod'),
                    ('ozodbek', 'G\'ulomov Ozodbek')):
        found = any(os.path.exists(os.path.join(PHOTO_DIR, fn + e))
                    for e in ('.jpg', '.jpeg', '.JPG', '.JPEG'))
        print('    [%s] %-20s %s' % ('v' if found else ' ', fn + '.jpg', who))
        if not found:
            missing.append(fn)
    if missing:
        print('')
        print('    Rasmi yo\'qlar uchun bosh harflar chiziladi (muammo emas).')
        print('    Rasm qo\'shish: team_photos papkasiga .jpg tashlang.')
    print('')

    if sys.platform.startswith('win'):
        try:
            os.startfile(out)
        except Exception:
            pass


if __name__ == '__main__':
    main()
