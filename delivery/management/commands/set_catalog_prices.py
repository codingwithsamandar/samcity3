"""Katalog mahsulotlariga tavsiya narx (suggested_price) qo'yadi — ommaviy, idempotent.

    python manage.py set_catalog_prices            # faqat narxsizlarga qo'yadi
    python manage.py set_catalog_prices --dry-run  # ko'rsatadi, yozmaydi
    python manage.py set_catalog_prices --force    # mavjud narxlarni ham qayta yozadi

Narxlar o'zbekcha (yakuniy) nom bo'yicha biriktiriladi — shuning uchun bu buyruq
`translate_catalog`dan KEYIN ishlashi kerak (entrypoint.sh shunday tartibda).

Idempotent: standart holatda faqat `suggested_price IS NULL` bo'lgan yozuvlarga
tegadi — admin panelida qo'lda o'zgartirilgan narxlar saqlanib qoladi. --force
berilsa, xaritadagi barcha narxlar qayta yoziladi.

Narxlar — 2026 yil O'zbekiston chakana bozori uchun taxminiy tavsiya qiymatlar
(so'mda). Do'kon egasi qo'shishdan oldin kartochkada o'zgartira oladi.
"""
from django.core.management.base import BaseCommand

from delivery.models import CatalogProduct

# O'zbekcha (yakuniy) nom -> tavsiya narx (so'm). translate_catalog'dagi nomlar bilan bir xil.
PRICES = {
    # ── Ichimliklar ──
    "7UP 1L": 12000,
    "Coca-Cola 1L": 12000,
    "Coca-Cola Zero 0.5L": 8000,
    "Fanta Orange 1L": 12000,
    "Sprite 1L": 12000,
    "Pepsi 1.5L": 14000,
    "Mirinda Orange 1L": 12000,
    "Adrenaline Rush energetik ichimlik 0.5L": 15000,
    "Red Bull energetik ichimlik 250ml": 22000,
    "Ahmad Tea ko'k choy 100g": 25000,
    "Lipton Yellow Label choy 100 paket": 45000,
    "Nescafe Classic eritma qahva 190g": 75000,
    "Jacobs Monarch tuyulgan qahva 250g": 55000,
    "Chortoq mineral suvi 1L": 4000,
    "Hydrolife gazsiz suv 1.5L": 4000,
    "Nestle Pure Life suvi 5L": 12000,
    "Piko olma sharbati 1L": 15000,
    "Piko shaftoli nektari 1L": 15000,
    "Piko pomidor sharbati 1L": 15000,
    "Rich apelsin sharbati 1L": 22000,
    "Nesquik shokoladli sut 200ml": 8000,
    # ── Sut mahsulotlari ──
    "Activia natural yogurt 290g": 12000,
    "Pasterlangan sut 2.5% 1L": 13000,
    "UHT sut 3.2% 1L": 14000,
    "Kefir 2.5% 500ml": 9000,
    "Qatiq 3.2% 500g": 10000,
    "Suzma 400g": 15000,
    "Ayron 0.5L": 7000,
    "Smetana 20% 400g": 16000,
    "Qulupnayli yogurt 290g": 12000,
    "Sariyog' 82.5% 200g": 22000,
    "Hochland krem pishloq 180g": 25000,
    "Suluguni pishlog'i 300g": 35000,
    "Quyultirilgan sut 380g": 18000,
    "Tovuq tuxumi C0 30 dona": 45000,
    "Tovuq tuxumi C1 10 dona": 15000,
    "Tuxum 10 dona": 14000,
    "Sut 1L": 13000,
    # ── Go'sht va baliq ──
    "Mol go'shti fileti 1kg": 110000,
    "Mol go'shti qiymasi 500g": 55000,
    "Mol go'shtli sosiska 400g": 35000,
    "«Doktorskaya» qaynatilgan kolbasa 500g": 45000,
    "Dudlangan mol salami 300g": 55000,
    "Qazi (ot go'shti) 300g": 90000,
    "Tovuq son-boldiri 1kg": 40000,
    "Tovuq fileti 1kg": 55000,
    "Butun tovuq 1.5kg": 65000,
    "Qo'y qovurg'asi 1kg": 95000,
    "Muzlatilgan skumbriya 1kg": 45000,
    # ── Meva va sabzavot ──
    "Banan 1kg": 18000,
    "Golden olma 1kg": 15000,
    "Apelsin 1kg": 18000,
    "Husayni uzumi 1kg": 25000,
    "Tarvuz": 25000,
    "Mirzacho'l qovuni": 30000,
    "Anor 1kg": 22000,
    "Limon 500g": 12000,
    "Kartoshka 1kg": 6000,
    "Piyoz 1kg": 5000,
    "Sabzi 1kg": 6000,
    "Pomidor 1kg": 12000,
    "Bodring 1kg": 10000,
    "Bulg'or qalampiri 500g": 12000,
    "Sarimsoq 200g": 12000,
    "Oq karam": 7000,
    "Yangi shivit": 3000,
    "Yangi kashnich": 3000,
    # ── Oshxona / yormalar ──
    "Devzira guruchi 1kg": 28000,
    "Lazer guruchi 1kg": 16000,
    "Grechka yormasi 800g": 18000,
    "Suli xlopyasi 500g": 14000,
    "Bug'doy uni, oliy nav 2kg": 16000,
    "Shakar (qum) 1kg": 12000,
    "Yodlangan tuz 1kg": 3500,
    "Kungaboqar yog'i 5L": 95000,
    "Paxta yog'i 1L": 22000,
    "Oleina kungaboqar yog'i 1L": 24000,
    "Borges zaytun yog'i 500ml": 75000,
    "Makfa spagetti 450g": 14000,
    "Vermishel 400g": 10000,
    "Doshirak lag'moni, tovuq ta'mli 90g": 6000,
    "Tomat pastasi 500g": 18000,
    "Heinz ketchup 350g": 28000,
    "Mayonez 67% 400g": 18000,
    "Soya sousi 200ml": 15000,
    "Achchiq adjika sousi 300g": 18000,
    "Sirka 9% 500ml": 6000,
    "Tuzlangan bodring 900g": 22000,
    "Konserva no'xat 400g": 12000,
    "Yog'dagi tunes konservasi 185g": 22000,
    "Tabiiy asal 500g": 65000,
    "Quritilgan o'rik (turshak) 500g": 35000,
    "Mayiz 500g": 30000,
    "Yong'oq mag'zi 300g": 45000,
    "Tuzlangan yeryong'oq 200g": 14000,
    "Zira 50g": 8000,
    "Tuyulgan qora murch 50g": 10000,
    "Paprika (qizil murch) 50g": 8000,
    # ── Non mahsulotlari ──
    "Obi non": 4000,
    "Patir non": 5000,
    "Yupqa lavash 200g": 6000,
    "Bo'laklangan oq non 500g": 9000,
    "Javdar non 400g": 12000,
    "Saf-Moment quruq achitqi 11g": 4000,
    "Dr. Oetker xamirturush kukuni 10g": 5000,
    "Non (tandir)": 4000,
    # ── Shirinliklar / gazaklar ──
    "Alpen Gold funduqli shokolad 85g": 15000,
    "KitKat 4 tayoqcha 41g": 10000,
    "Milka Alp sutli shokoladi 90g": 22000,
    "Snickers batonchik 50g": 8000,
    "Mars batonchik 51g": 8000,
    "Twix batonchik 55g": 8000,
    "Oreo pechenyesi 95g": 12000,
    "Barni biskvit keksi 30g": 4000,
    "Shokoladli vafli 220g": 15000,
    "«Yubileynoye» pechenyesi 112g": 10000,
    "Tuzli kreker 180g": 12000,
    "Kungaboqar halvo 350g": 22000,
    "Lay's Classic chipsi 80g": 15000,
    "Lay's smetana-piyoz chipsi 80g": 15000,
    "Pringles Original 165g": 35000,
    "Tuzli popkorn 100g": 10000,
    "Vanilli plombir muzqaymoq 400g": 25000,
    "Shokoladli muzqaymoq (rojok) 100g": 8000,
    # ── Uy-ro'zg'or ──
    "Ariel kir yuvish kukuni 3kg": 85000,
    "Tide kir yuvish kukuni 3kg": 80000,
    "Persil suyuq kir vositasi 1.3L": 75000,
    "Lenor kir yumshatgichi 1L": 45000,
    "Fairy idish yuvish vositasi 900ml": 38000,
    "Domestos oqartirgich 1L": 28000,
    "Pol yuvish vositasi 1L": 22000,
    "Oyna tozalash spreyi 500ml": 22000,
    "Hojatxona qog'ozi 8 rulon": 28000,
    "Qog'oz sochiq 2 rulon": 18000,
    "Qog'oz salfetka 100 dona": 8000,
    "Chiqindi paketi 30L 20 dona": 15000,
    "Oziq-ovqat plyonkasi 30m": 15000,
    "Alyumin folga 10m": 18000,
    "Oshxona gubkasi 5 dona": 10000,
    # ── Shaxsiy gigiyena ──
    "Colgate tish pastasi 100ml": 22000,
    "Sensodyne tish pastasi 75ml": 45000,
    "Tish cho'tkasi, o'rtacha": 12000,
    "Head & Shoulders shampuni 400ml": 55000,
    "Pantene Pro-V shampuni 400ml": 55000,
    "Schauma shampuni 400ml": 35000,
    "Bolalar shampuni 200ml": 28000,
    "Dove go'zallik sovuni 100g": 12000,
    "Safeguard sovuni 90g": 8000,
    "Nivea Soft kremi 75ml": 35000,
    "Rexona dezodorant spreyi 150ml": 35000,
    "Gillette ustarasi, 3 tig'li": 25000,
    # ── Bolalar ──
    "Bolalar nam salfetkasi 72 dona": 18000,
    "Pampers tagliklari, 4-o'lcham 58 dona": 95000,
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
