"""Katalog mahsulotlariga tavsiya narx (suggested_price) qo'yadi — ommaviy, idempotent.

    python manage.py set_catalog_prices            # faqat narxsizlarga qo'yadi
    python manage.py set_catalog_prices --dry-run  # ko'rsatadi, yozmaydi
    python manage.py set_catalog_prices --force    # mavjud narxlarni ham qayta yozadi

Narxlar o'zbekcha (yakuniy) nom bo'yicha biriktiriladi — shuning uchun bu buyruq
`translate_catalog`dan KEYIN ishlashi kerak (entrypoint.sh shunday tartibda).

Idempotent: standart holatda faqat `suggested_price IS NULL` bo'lgan yozuvlarga
tegadi — admin panelida qo'lda o'zgartirilgan narxlar saqlanib qoladi. --force
berilsa, xaritadagi barcha narxlar qayta yoziladi.

Narxlar — Shofirkon (Buxoro viloyati) mahalliy bozoriga moslangan tavsiya
qiymatlar (so'mda). Avval Korzinka (2026 may-iyun), Numbeo Toshkent (2026) va
Milliy statistika langarlariga kalibrlangan, so'ng kichik shahar sharoitiga
biroz arzonlashtirilgan: mahalliy/yangi mahsulotlar (go'sht ~−10%,
meva-sabzavot ~−15%, sut/non ~−10%), import/brendli tovarlar ~−5% (ular
mamlakat bo'ylab deyarli bir xil narxlanadi). Masalan tovuq fileti ~47k,
mol go'shti fileti ~117k, sut ~12.5k, tandir non 2.5k. Yangi meva-sabzavot
mavsumga qarab o'zgaradi. Do'kon egasi qo'shishdan oldin kartochkada narxni
o'zgartira oladi.
"""
from django.core.management.base import BaseCommand

from delivery.models import CatalogProduct

# O'zbekcha (yakuniy) nom -> tavsiya narx (so'm). translate_catalog'dagi nomlar bilan bir xil.
PRICES = {
    # Narxlar Shofirkon (Buxoro viloyati) mahalliy bozoriga moslangan — Toshkent
    # tarmoq narxidan biroz past: mahalliy/yangi mahsulotlar (go'sht ~−10%,
    # meva-sabzavot ~−15%, sut/non ~−10%), import/brendli tovarlar ~−5%.
    # ── Ichimliklar ──
    "7UP 1L": 10500,
    "Coca-Cola 1L": 11500,
    "Coca-Cola Zero 0.5L": 6500,
    "Fanta Orange 1L": 10500,
    "Sprite 1L": 10500,
    "Pepsi 1.5L": 12500,
    "Mirinda Orange 1L": 10500,
    "Adrenaline Rush energetik ichimlik 0.5L": 13000,
    "Red Bull energetik ichimlik 250ml": 19000,
    "Ahmad Tea ko'k choy 100g": 23000,
    "Lipton Yellow Label choy 100 paket": 45000,
    "Nescafe Classic eritma qahva 190g": 74000,
    "Jacobs Monarch tuyulgan qahva 250g": 59000,
    "Chortoq mineral suvi 1L": 3500,
    "Hydrolife gazsiz suv 1.5L": 3500,
    "Nestle Pure Life suvi 5L": 10500,
    "Piko olma sharbati 1L": 13500,
    "Piko shaftoli nektari 1L": 13500,
    "Piko pomidor sharbati 1L": 13500,
    "Rich apelsin sharbati 1L": 20000,
    "Nesquik shokoladli sut 200ml": 7500,
    # ── Sut mahsulotlari ──
    "Activia natural yogurt 290g": 11000,
    "Pasterlangan sut 2.5% 1L": 11500,
    "UHT sut 3.2% 1L": 13500,
    "Kefir 2.5% 500ml": 8000,
    "Qatiq 3.2% 500g": 9000,
    "Suzma 400g": 12500,
    "Ayron 0.5L": 5500,
    "Smetana 20% 400g": 14500,
    "Qulupnayli yogurt 290g": 11000,
    "Sariyog' 82.5% 200g": 21500,
    "Hochland krem pishloq 180g": 22500,
    "Suluguni pishlog'i 300g": 30000,
    "Quyultirilgan sut 380g": 15000,
    "Tovuq tuxumi C0 30 dona": 40000,
    "Tovuq tuxumi C1 10 dona": 14500,
    "Tuxum 10 dona": 13500,
    "Sut 1L": 12500,
    # ── Go'sht va baliq ──
    "Mol go'shti fileti 1kg": 117000,
    "Mol go'shti qiymasi 500g": 47000,
    "Mol go'shtli sosiska 400g": 30000,
    "«Doktorskaya» qaynatilgan kolbasa 500g": 40000,
    "Dudlangan mol salami 300g": 47000,
    "Qazi (ot go'shti) 300g": 85000,
    "Tovuq son-boldiri 1kg": 34000,
    "Tovuq fileti 1kg": 47000,
    "Butun tovuq 1.5kg": 47000,
    "Qo'y qovurg'asi 1kg": 108000,
    "Muzlatilgan skumbriya 1kg": 38000,
    # ── Meva va sabzavot ──
    "Banan 1kg": 16000,
    "Golden olma 1kg": 13500,
    "Apelsin 1kg": 15000,
    "Husayni uzumi 1kg": 21000,
    "Tarvuz": 20000,
    "Mirzacho'l qovuni": 25000,
    "Anor 1kg": 18500,
    "Limon 500g": 10000,
    "Kartoshka 1kg": 6000,
    "Piyoz 1kg": 4500,
    "Sabzi 1kg": 6000,
    "Pomidor 1kg": 12000,
    "Bodring 1kg": 9500,
    "Bulg'or qalampiri 500g": 10000,
    "Sarimsoq 200g": 10000,
    "Oq karam": 6000,
    "Yangi shivit": 2500,
    "Yangi kashnich": 2500,
    # ── Oshxona / yormalar ──
    "Devzira guruchi 1kg": 27000,
    "Lazer guruchi 1kg": 16000,
    "Grechka yormasi 800g": 16000,
    "Suli xlopyasi 500g": 12500,
    "Bug'doy uni, oliy nav 2kg": 14500,
    "Shakar (qum) 1kg": 10500,
    "Yodlangan tuz 1kg": 3000,
    "Kungaboqar yog'i 5L": 88000,
    "Paxta yog'i 1L": 20000,
    "Oleina kungaboqar yog'i 1L": 22000,
    "Borges zaytun yog'i 500ml": 71000,
    "Makfa spagetti 450g": 13000,
    "Vermishel 400g": 9000,
    "Doshirak lag'moni, tovuq ta'mli 90g": 5500,
    "Tomat pastasi 500g": 16000,
    "Heinz ketchup 350g": 27000,
    "Mayonez 67% 400g": 16000,
    "Soya sousi 200ml": 14000,
    "Achchiq adjika sousi 300g": 16000,
    "Sirka 9% 500ml": 5500,
    "Tuzlangan bodring 900g": 20000,
    "Konserva no'xat 400g": 11000,
    "Yog'dagi tunes konservasi 185g": 21000,
    "Tabiiy asal 500g": 58000,
    "Quritilgan o'rik (turshak) 500g": 31000,
    "Mayiz 500g": 27000,
    "Yong'oq mag'zi 300g": 40000,
    "Tuzlangan yeryong'oq 200g": 12500,
    "Zira 50g": 7000,
    "Tuyulgan qora murch 50g": 9000,
    "Paprika (qizil murch) 50g": 7000,
    # ── Non mahsulotlari ──
    "Obi non": 2500,
    "Patir non": 3500,
    "Yupqa lavash 200g": 4500,
    "Bo'laklangan oq non 500g": 8000,
    "Javdar non 400g": 10000,
    "Saf-Moment quruq achitqi 11g": 3500,
    "Dr. Oetker xamirturush kukuni 10g": 4500,
    "Non (tandir)": 2500,
    # ── Shirinliklar / gazaklar ──
    "Alpen Gold funduqli shokolad 85g": 14000,
    "KitKat 4 tayoqcha 41g": 9500,
    "Milka Alp sutli shokoladi 90g": 21000,
    "Snickers batonchik 50g": 7500,
    "Mars batonchik 51g": 7500,
    "Twix batonchik 55g": 7500,
    "Oreo pechenyesi 95g": 11000,
    "Barni biskvit keksi 30g": 3500,
    "Shokoladli vafli 220g": 14000,
    "«Yubileynoye» pechenyesi 112g": 9500,
    "Tuzli kreker 180g": 11000,
    "Kungaboqar halvo 350g": 20000,
    "Lay's Classic chipsi 80g": 14000,
    "Lay's smetana-piyoz chipsi 80g": 14000,
    "Pringles Original 165g": 33000,
    "Tuzli popkorn 100g": 9000,
    "Vanilli plombir muzqaymoq 400g": 23000,
    "Shokoladli muzqaymoq (rojok) 100g": 7500,
    # ── Uy-ro'zg'or ──
    "Ariel kir yuvish kukuni 3kg": 80000,
    "Tide kir yuvish kukuni 3kg": 76000,
    "Persil suyuq kir vositasi 1.3L": 71000,
    "Lenor kir yumshatgichi 1L": 42000,
    "Fairy idish yuvish vositasi 900ml": 36000,
    "Domestos oqartirgich 1L": 27000,
    "Pol yuvish vositasi 1L": 20000,
    "Oyna tozalash spreyi 500ml": 20000,
    "Hojatxona qog'ozi 8 rulon": 26000,
    "Qog'oz sochiq 2 rulon": 17000,
    "Qog'oz salfetka 100 dona": 7500,
    "Chiqindi paketi 30L 20 dona": 14000,
    "Oziq-ovqat plyonkasi 30m": 14000,
    "Alyumin folga 10m": 17000,
    "Oshxona gubkasi 5 dona": 9000,
    # ── Shaxsiy gigiyena ──
    "Colgate tish pastasi 100ml": 21000,
    "Sensodyne tish pastasi 75ml": 42000,
    "Tish cho'tkasi, o'rtacha": 11000,
    "Head & Shoulders shampuni 400ml": 52000,
    "Pantene Pro-V shampuni 400ml": 52000,
    "Schauma shampuni 400ml": 33000,
    "Bolalar shampuni 200ml": 26000,
    "Dove go'zallik sovuni 100g": 11000,
    "Safeguard sovuni 90g": 7500,
    "Nivea Soft kremi 75ml": 33000,
    "Rexona dezodorant spreyi 150ml": 33000,
    "Gillette ustarasi, 3 tig'li": 24000,
    # ── Bolalar ──
    "Bolalar nam salfetkasi 72 dona": 17000,
    "Pampers tagliklari, 4-o'lcham 58 dona": 90000,
}


class Command(BaseCommand):
    help = "Katalog mahsulotlariga tavsiya narx qo'yadi (o'zbekcha nom bo'yicha, idempotent)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Hech narsa yozmasdan ko'rsatadi")
        parser.add_argument('--force', action='store_true',
                            help="Mavjud narxlarni ham qayta yozadi (aks holda faqat narxsizlar)")

    def handle(self, *args, **opts):
        dry, force = opts['dry_run'], opts['force']
        set_count = skipped_existing = 0
        not_found = []       # xaritada bor, bazada yo'q
        for name, price in PRICES.items():
            obj = CatalogProduct.objects.filter(name__iexact=name).first()
            if obj is None:
                not_found.append(name)
                continue
            if obj.suggested_price is not None and not force:
                skipped_existing += 1
                continue
            obj.suggested_price = price
            if not dry:
                obj.save(update_fields=['suggested_price', 'updated_at'])
            set_count += 1

        # Narxsiz qolgan faol mahsulotlar (xaritada nomi topilmadi) — diqqat uchun.
        no_price = list(CatalogProduct.objects.filter(
            is_active=True, suggested_price__isnull=True)
            .values_list('name', flat=True))

        mode = "DRY-RUN (yozilmadi)" if dry else "QO'LLANDI"
        self.stdout.write(self.style.SUCCESS(
            f"[{mode}] narx qo'yildi: {set_count}, "
            f"o'tkazildi (narxi bor): {skipped_existing}, xaritada: {len(PRICES)}"))
        if not_found:
            self.stdout.write(self.style.WARNING(
                f"Xaritada bor, bazada topilmadi ({len(not_found)}): "
                + ", ".join(not_found[:20]) + ("..." if len(not_found) > 20 else "")))
        if no_price and not dry:
            self.stdout.write(self.style.WARNING(
                f"Hali narxsiz faol mahsulot ({len(no_price)}): "
                + ", ".join(no_price[:20]) + ("..." if len(no_price) > 20 else "")))
