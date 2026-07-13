"""Katalog mahsulot nomlari va tavsiflarini o'zbekchaga o'giradi (idempotent).

    python manage.py translate_catalog            # qo'llaydi
    python manage.py translate_catalog --dry-run  # ko'rsatadi, yozmaydi

Import ma'lumotlari inglizcha edi ("Chicken Eggs C0 30 pcs"). Bu buyruq har
bir mahsulotni INGLIZCHA nomi bo'yicha topib, o'zbekcha nom/tavsif bilan
yangilaydi. Brend nomlari (Coca-Cola, Ariel...) va o'lchamlar (1L, 500g)
saqlanadi. Idempotent: allaqachon o'girilgan (inglizcha nomi topilmagan)
yozuvlar o'tkazib yuboriladi, shuning uchun qayta ishga tushirish xavfsiz.
"""
from django.core.management.base import BaseCommand

from delivery.models import CatalogProduct

# Inglizcha nom -> (o'zbekcha nom, o'zbekcha tavsif)
TRANSLATIONS = {
    # ── Ichimliklar ──
    "7UP 1L": ("7UP 1L", "Kofeinsiz limon-laym gazli ichimlik."),
    "Coca-Cola 1L": ("Coca-Cola 1L", "Klassik gazli kola ichimligi, 1 litrlik PET shisha."),
    "Coca-Cola Zero 0.5L": ("Coca-Cola Zero 0.5L", "Shakarsiz kola — klassik Coca-Cola ta'mi bilan."),
    "Fanta Orange 1L": ("Fanta Orange 1L", "Apelsin ta'mli gazli ichimlik."),
    "Sprite 1L": ("Sprite 1L", "Gazli limon-laym ichimlik."),
    "Pepsi 1.5L": ("Pepsi 1.5L", "Gazli kola ichimlik, oilaviy 1.5 litrlik shisha."),
    "Mirinda Orange 1L": ("Mirinda Orange 1L", "Gazli apelsin ichimlik."),
    "Adrenaline Rush Energy Drink 0.5L": ("Adrenaline Rush energetik ichimlik 0.5L", "Guarana va B guruh vitaminli energetik ichimlik."),
    "Red Bull Energy Drink 250ml": ("Red Bull energetik ichimlik 250ml", "Kofein va taurinli gazli energetik ichimlik."),
    "Ahmad Tea Green Tea 100g": ("Ahmad Tea ko'k choy 100g", "Yaproqli ko'k choy, 100 g."),
    "Lipton Yellow Label Tea 100 Bags": ("Lipton Yellow Label choy 100 paket", "Qora choy, 100 ta bir martalik paketda."),
    "Nescafe Classic Instant Coffee 190g": ("Nescafe Classic eritma qahva 190g", "Eritma qahva donachalari, 190 g shisha idishda."),
    "Jacobs Monarch Ground Coffee 250g": ("Jacobs Monarch tuyulgan qahva 250g", "Qovurilgan va tuyulgan qahva, 250 g vakuum paket."),
    "Chortoq Mineral Water 1L": ("Chortoq mineral suvi 1L", "Chortoq bulog'idan tabiiy mineral suv."),
    "Hydrolife Still Water 1.5L": ("Hydrolife gazsiz suv 1.5L", "Gazsiz ichimlik suvi, 1.5 litrlik shisha."),
    "Nestle Pure Life Water 5L": ("Nestle Pure Life suvi 5L", "Tozalangan gazsiz ichimlik suvi, 5 litrlik idish."),
    "Piko Apple Juice 1L": ("Piko olma sharbati 1L", "Olma sharbati, 1 litrlik karton paket."),
    "Piko Peach Nectar 1L": ("Piko shaftoli nektari 1L", "Meva bo'lakli shaftoli nektari, karton paket."),
    "Piko Tomato Juice 1L": ("Piko pomidor sharbati 1L", "Bir chimdim tuz qo'shilgan pomidor sharbati."),
    "Rich Orange Juice 1L": ("Rich apelsin sharbati 1L", "100% apelsin sharbati, 1 litrlik karton."),
    "Nesquik Chocolate Milk 200ml": ("Nesquik shokoladli sut 200ml", "Bolalar uchun shokolad ta'mli sut ichimlik."),
    # ── Sut mahsulotlari ──
    "Activia Natural Yogurt 290g": ("Activia natural yogurt 290g", "Probiotik madaniyatli natural yogurt."),
    "Pasteurized Milk 2.5% 1L": ("Pasterlangan sut 2.5% 1L", "Pasterlangan sigir suti, 2.5% yog', 1 litrlik shisha."),
    "UHT Milk 3.2% 1L": ("UHT sut 3.2% 1L", "Ultra-pasterlangan sut, 3.2% yog', uzoq saqlanadi."),
    "Kefir 2.5% 500ml": ("Kefir 2.5% 500ml", "Tirik madaniyatli achitilgan sut ichimlik."),
    "Qatiq 3.2% 500g": ("Qatiq 3.2% 500g", "An'anaviy o'zbek achitilgan sut mahsuloti."),
    "Suzma 400g": ("Suzma 400g", "Quyuq, qaymoqsimon suzilgan qatiq."),
    "Ayran 0.5L": ("Ayron 0.5L", "Tuzlangan yogurt ichimlik, sovutib ichiladi."),
    "Sour Cream 20% 400g": ("Smetana 20% 400g", "Smetana qaymoq, 20% yog'."),
    "Strawberry Yogurt 290g": ("Qulupnayli yogurt 290g", "Qulupnay bo'lakli qaymoqli yogurt."),
    "Butter 82.5% 200g": ("Sariyog' 82.5% 200g", "Qaymoqli sariyog', 82.5% yog'."),
    "Hochland Cream Cheese 180g": ("Hochland krem pishloq 180g", "Buterbrod uchun yumshoq krem pishloq."),
    "Suluguni Cheese 300g": ("Suluguni pishlog'i 300g", "Yarim qattiq tuzlangan pishloq, mayin sho'r ta'mli."),
    "Condensed Milk 380g": ("Quyultirilgan sut 380g", "Shirin quyultirilgan sut — shirinlik va qahva uchun."),
    "Chicken Eggs C0 30 pcs": ("Tovuq tuxumi C0 30 dona", "Yangi C0 nav tovuq tuxumi, 30 donalik."),
    "Chicken Eggs C1 10 pcs": ("Tovuq tuxumi C1 10 dona", "Yangi C1 nav tovuq tuxumi, 10 donalik."),
    # ── Go'sht va baliq ──
    "Beef Tenderloin 1kg": ("Mol go'shti fileti 1kg", "Sovutilgan mol go'shti fileti, tarozida sotiladi."),
    "Ground Beef 500g": ("Mol go'shti qiymasi 500g", "Yangi qiyilgan mol go'shti, 500 g."),
    "Beef Sausages 400g": ("Mol go'shtli sosiska 400g", "Qaynatish yoki qovurishga tayyor mol sosiska."),
    "Doctor's Boiled Sausage 500g": ("«Doktorskaya» qaynatilgan kolbasa 500g", "Mayin ta'mli klassik qaynatilgan kolbasa."),
    "Smoked Beef Salami 300g": ("Dudlangan mol salami 300g", "Quritib dudlangan mol go'shtli salami."),
    "Kazi Horse Sausage 300g": ("Qazi (ot go'shti) 300g", "An'anaviy ot go'shtli hasib — bayramona noz-ne'mat."),
    "Chicken Drumsticks 1kg": ("Tovuq son-boldiri 1kg", "Sovutilgan tovuq boldiri, tarozida sotiladi."),
    "Chicken Fillet 1kg": ("Tovuq fileti 1kg", "Terisiz tovuq ko'krak fileti, sovutilgan."),
    "Whole Chicken 1.5kg": ("Butun tovuq 1.5kg", "Sovutilgan butun broyler tovuq, ~1.5 kg."),
    "Lamb Ribs 1kg": ("Qo'y qovurg'asi 1kg", "Panjara va qovurma uchun sovutilgan qo'y qovurg'asi."),
    "Frozen Mackerel 1kg": ("Muzlatilgan skumbriya 1kg", "Butun muzlatilgan skumbriya, tarozida sotiladi."),
    # ── Meva va sabzavot ──
    "Bananas 1kg": ("Banan 1kg", "Yetilgan import banan, tarozida sotiladi."),
    "Golden Apples 1kg": ("Golden olma 1kg", "Shirin Golden nav olma, tarozida sotiladi."),
    "Oranges 1kg": ("Apelsin 1kg", "Sersuv shirin apelsin, tarozida sotiladi."),
    "Husayni Grapes 1kg": ("Husayni uzumi 1kg", "Uzun shirin Husayni uzumi."),
    "Watermelon": ("Tarvuz", "Mavsumiy butun tarvuz."),
    "Mirzachul Melon": ("Mirzacho'l qovuni", "Xushbo'y Mirzacho'l qovuni — mahalliy sevimli."),
    "Pomegranate 1kg": ("Anor 1kg", "To'q qizil donali yetilgan anor."),
    "Lemons 500g": ("Limon 500g", "Yangi limon, 500 g."),
    "Potatoes 1kg": ("Kartoshka 1kg", "Qaynatish va qovurish uchun kartoshka."),
    "Onions 1kg": ("Piyoz 1kg", "Sariq oshxona piyozi, tarozida sotiladi."),
    "Carrots 1kg": ("Sabzi 1kg", "Yangi sabzi — palov uchun zarur."),
    "Tomatoes 1kg": ("Pomidor 1kg", "Yetilgan salat pomidori, tarozida sotiladi."),
    "Cucumbers 1kg": ("Bodring 1kg", "Yangi qarsildoq bodring, tarozida sotiladi."),
    "Bell Peppers 500g": ("Bulg'or qalampiri 500g", "Turli rangdagi shirin bulg'or qalampiri."),
    "Garlic 200g": ("Sarimsoq 200g", "Yangi sarimsoq boshlari, 200 g."),
    "White Cabbage": ("Oq karam", "Yangi oq karam boshi."),
    "Fresh Dill": ("Yangi shivit", "Xushbo'y yangi shivit, bog'lam bilan."),
    "Fresh Cilantro": ("Yangi kashnich", "Yangi kashnich barglari, bog'lam bilan."),
    # ── Oshxona / yormalar ──
    "Devzira Rice 1kg": ("Devzira guruchi 1kg", "An'anaviy Devzira guruchi — palovga ideal."),
    "Lazer Rice 1kg": ("Lazer guruchi 1kg", "Kundalik taom uchun uzun donli Lazer guruchi."),
    "Buckwheat Groats 800g": ("Grechka yormasi 800g", "Qovurilgan grechka yormasi, 800 g."),
    "Oat Flakes 500g": ("Suli xlopyasi 500g", "Bo'tqa va pishiriq uchun suli xlopyasi."),
    "Wheat Flour Premium 2kg": ("Bug'doy uni, oliy nav 2kg", "Pishiriq uchun oliy nav bug'doy uni."),
    "Granulated Sugar 1kg": ("Shakar (qum) 1kg", "Oq shakar-qum, 1 kg."),
    "Iodized Salt 1kg": ("Yodlangan tuz 1kg", "Mayda yodlangan oshxona tuzi."),
    "Sunflower Oil 5L": ("Kungaboqar yog'i 5L", "Tozalangan kungaboqar yog'i, 5 litrlik idish."),
    "Cottonseed Oil 1L": ("Paxta yog'i 1L", "An'anaviy paxta yog'i — palov uchun keng ishlatiladi."),
    "Oleina Sunflower Oil 1L": ("Oleina kungaboqar yog'i 1L", "Qovurish va salat uchun tozalangan kungaboqar yog'i."),
    "Borges Olive Oil 500ml": ("Borges zaytun yog'i 500ml", "Extra virgin zaytun yog'i, shisha idishda."),
    "Makfa Spaghetti 450g": ("Makfa spagetti 450g", "Qattiq bug'doy spagettisi, 450 g."),
    "Vermicelli 400g": ("Vermishel 400g", "Sho'rva va garnir uchun ingichka bug'doy vermisheli."),
    "Doshirak Instant Noodles Chicken 90g": ("Doshirak lag'moni, tovuq ta'mli 90g", "Tovuq ta'mli ziravorli tez tayyor lag'mon."),
    "Tomato Paste 500g": ("Tomat pastasi 500g", "Konsentrlangan tomat pastasi, shisha idishda."),
    "Heinz Ketchup 350g": ("Heinz ketchup 350g", "Klassik pomidor ketchupi, siqiladigan shishada."),
    "Mayonnaise 67% 400g": ("Mayonez 67% 400g", "Provansal mayonez, 67% yog'."),
    "Soy Sauce 200ml": ("Soya sousi 200ml", "Tabiiy achitilgan soya sousi."),
    "Chili Adjika Sauce 300g": ("Achchiq adjika sousi 300g", "Chili va sarimsoqli achchiq adjika."),
    "Table Vinegar 9% 500ml": ("Sirka 9% 500ml", "Marinad va salat uchun oshxona sirkasi."),
    "Pickled Cucumbers 900g": ("Tuzlangan bodring 900g", "Sho'rda qarsildoq tuzlangan bodring."),
    "Canned Green Peas 400g": ("Konserva no'xat 400g", "Sho'rdagi mayin yashil no'xat."),
    "Canned Tuna in Oil 185g": ("Yog'dagi tunes konservasi 185g", "Kungaboqar yog'idagi tunes bo'laklari."),
    "Natural Honey 500g": ("Tabiiy asal 500g", "Shisha idishdagi tabiiy gul asali."),
    "Dried Apricots 500g": ("Quritilgan o'rik (turshak) 500g", "Mahalliy bog'lardan shirin turshak."),
    "Raisins 500g": ("Mayiz 500g", "Danaksiz quyoshda quritilgan mayiz."),
    "Walnut Kernels 300g": ("Yong'oq mag'zi 300g", "Tozalangan yong'oq mag'zi, tayyor."),
    "Salted Peanuts 200g": ("Tuzlangan yeryong'oq 200g", "Qovurilgan va tuzlangan yeryong'oq."),
    "Cumin Seeds (Zira) 50g": ("Zira 50g", "Butun zira — palov uchun zarur ziravor."),
    "Ground Black Pepper 50g": ("Tuyulgan qora murch 50g", "Mayda tuyulgan qora murch."),
    "Paprika Powder 50g": ("Paprika (qizil murch) 50g", "Mayin tuyulgan shirin paprika."),
    # ── Non mahsulotlari ──
    "Obi Non Flatbread": ("Obi non", "Har kuni pishiriladigan an'anaviy o'zbek tandir noni."),
    "Patyr Non Flatbread": ("Patir non", "Oltinrang qatlamli boy tandir noni."),
    "Lavash Thin Flatbread 200g": ("Yupqa lavash 200g", "O'rama uchun yupqa xamirturushsiz non."),
    "Sliced White Bread 500g": ("Bo'laklangan oq non 500g", "Yumshoq oq buterbrod noni, bo'laklangan."),
    "Rye Bread 400g": ("Javdar non 400g", "Zich mag'izli to'q javdar noni."),
    "Saf-Moment Dry Yeast 11g": ("Saf-Moment quruq achitqi 11g", "Non va xamir uchun tez achitqi."),
    "Dr. Oetker Baking Powder 10g": ("Dr. Oetker xamirturush kukuni 10g", "Tort va pishiriqlar uchun xamirturush kukuni."),
    # ── Shirinliklar / gazaklar ──
    "Alpen Gold Hazelnut Chocolate 85g": ("Alpen Gold funduqli shokolad 85g", "Funduq bo'lakli sutli shokolad."),
    "KitKat 4 Fingers 41g": ("KitKat 4 tayoqcha 41g", "Sutli shokoladli qarsildoq vafli tayoqchalar."),
    "Milka Alpine Milk Chocolate 90g": ("Milka Alp sutli shokoladi 90g", "Mayin Alp sutli shokolad plitkasi."),
    "Snickers Bar 50g": ("Snickers batonchik 50g", "Yeryong'oq, karamel va nugatli shokolad batonchik."),
    "Mars Bar 51g": ("Mars batonchik 51g", "Yumshoq nugat va karamelli shokolad batonchik."),
    "Twix Bar 55g": ("Twix batonchik 55g", "Karamel va shokoladli juft pechenye tayoqchalar."),
    "Oreo Cookies 95g": ("Oreo pechenyesi 95g", "Vanil kremli kakaoli sendvich pechenye."),
    "Barni Sponge Cake 30g": ("Barni biskvit keksi 30g", "Shokolad ichlikli yumshoq biskvit."),
    "Chocolate Wafers 220g": ("Shokoladli vafli 220g", "Shokolad kremli qatlamli qarsildoq vafli."),
    "Yubileynoye Cookies 112g": ("«Yubileynoye» pechenyesi 112g", "Klassik qarsildoq choy pechenyesi."),
    "Salted Crackers 180g": ("Tuzli kreker 180g", "Yengil tuzli kreker."),
    "Sunflower Halva 350g": ("Kungaboqar halvo 350g", "An'anaviy kungaboqar urug'idan halvo."),
    "Lay's Classic Chips 80g": ("Lay's Classic chipsi 80g", "Tuzli kartoshka chipsi, 80 g."),
    "Lay's Sour Cream & Onion 80g": ("Lay's smetana-piyoz chipsi 80g", "Smetana va piyoz ta'mli kartoshka chipsi."),
    "Pringles Original 165g": ("Pringles Original 165g", "Tubusdagi tuzli kartoshka chipsi."),
    "Salted Popcorn 100g": ("Tuzli popkorn 100g", "Tayyor tuzli popkorn."),
    "Vanilla Plombir Ice Cream 400g": ("Vanilli plombir muzqaymoq 400g", "Qaymoqli vanilli plombir muzqaymoq."),
    "Chocolate Ice Cream Cone 100g": ("Shokoladli muzqaymoq (rojok) 100g", "Shokoladli muzqaymoqli vafli rojok."),
    # ── Uy-ro'zg'or ──
    "Ariel Washing Powder 3kg": ("Ariel kir yuvish kukuni 3kg", "Oq va rangli kir uchun avtomat kukun."),
    "Tide Washing Powder 3kg": ("Tide kir yuvish kukuni 3kg", "Faol fermentli avtomat kir kukuni."),
    "Persil Liquid Detergent 1.3L": ("Persil suyuq kir vositasi 1.3L", "Mashinada yuvish uchun suyuq kir vositasi."),
    "Lenor Fabric Softener 1L": ("Lenor kir yumshatgichi 1L", "Uzoq hidli kir yumshatgich."),
    "Fairy Dishwashing Liquid 900ml": ("Fairy idish yuvish vositasi 900ml", "Konsentrlangan idish vositasi — yog'ni tez ketkazadi."),
    "Domestos Bleach 1L": ("Domestos oqartirgich 1L", "Hojatxona va qattiq sirtlar uchun quyuq oqartirgich."),
    "Floor Cleaner 1L": ("Pol yuvish vositasi 1L", "Yoqimli hidli ko'p sirtli pol vositasi."),
    "Glass Cleaner Spray 500ml": ("Oyna tozalash spreyi 500ml", "Oyna va ko'zgular uchun iz qoldirmaydigan sprey."),
    "Toilet Paper 8 Rolls": ("Hojatxona qog'ozi 8 rulon", "Ikki qatlamli hojatxona qog'ozi, 8 rulon."),
    "Paper Towels 2 Rolls": ("Qog'oz sochiq 2 rulon", "Namni yaxshi shimadigan oshxona qog'oz sochig'i, 2 rulon."),
    "Paper Napkins 100 pcs": ("Qog'oz salfetka 100 dona", "Oq dasturxon salfetkasi, 100 dona."),
    "Garbage Bags 30L 20 pcs": ("Chiqindi paketi 30L 20 dona", "Mustahkam chiqindi paketi, 30 litrlik, 20 dona."),
    "Cling Film 30m": ("Oziq-ovqat plyonkasi 30m", "Oziq-ovqatni o'rash uchun shaffof plyonka."),
    "Aluminium Foil 10m": ("Alyumin folga 10m", "Pishirish va saqlash uchun oziq-ovqat folgasi."),
    "Kitchen Sponges 5 pcs": ("Oshxona gubkasi 5 dona", "Ikki qatlamli idish yuvish gubkasi, 5 dona."),
    # ── Shaxsiy gigiyena ──
    "Colgate Toothpaste 100ml": ("Colgate tish pastasi 100ml", "Kariyesdan himoya qiluvchi ftorli tish pastasi."),
    "Sensodyne Toothpaste 75ml": ("Sensodyne tish pastasi 75ml", "Sezgir tishlar uchun tish pastasi."),
    "Toothbrush Medium": ("Tish cho'tkasi, o'rtacha", "Kundalik tozalash uchun o'rtacha qattiqlikdagi tish cho'tkasi."),
    "Head & Shoulders Shampoo 400ml": ("Head & Shoulders shampuni 400ml", "Kundalik uchun qazg'oqqa qarshi shampun."),
    "Pantene Pro-V Shampoo 400ml": ("Pantene Pro-V shampuni 400ml", "Shikastlangan soch uchun ozuqador shampun."),
    "Schauma Shampoo 400ml": ("Schauma shampuni 400ml", "O't-o'lan ekstraktli kundalik shampun."),
    "Baby Shampoo 200ml": ("Bolalar shampuni 200ml", "Nozik soch uchun ko'zni achitmaydigan bolalar shampuni."),
    "Dove Beauty Bar 100g": ("Dove go'zallik sovuni 100g", "Kremli namlaydigan go'zallik sovuni."),
    "Safeguard Soap 90g": ("Safeguard sovuni 90g", "Qo'l yuvish uchun antibakterial sovun."),
    "Nivea Soft Cream 75ml": ("Nivea Soft kremi 75ml", "Yuz, qo'l va tana uchun namlaydigan krem."),
    "Rexona Deodorant Spray 150ml": ("Rexona dezodorant spreyi 150ml", "48 soatlik terlashga qarshi dezodorant sprey."),
    "Gillette Razor 3 Blades": ("Gillette ustarasi, 3 tig'li", "Uch tig'li bir martalik ustara."),
    # ── Bolalar ──
    "Baby Wet Wipes 72 pcs": ("Bolalar nam salfetkasi 72 dona", "Hidsiz yumshoq bolalar salfetkasi."),
    "Pampers Diapers Size 4 58 pcs": ("Pampers tagliklari, 4-o'lcham 58 dona", "9-14 kg chaqaloqlar uchun yumshoq shimuvchi tagliklar."),
}


class Command(BaseCommand):
    help = "Katalog mahsulot nomlari va tavsiflarini o'zbekchaga o'giradi (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Hech narsa yozmasdan ko\'rsatadi')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        updated = skipped = 0
        for eng_name, (uz_name, uz_desc) in TRANSLATIONS.items():
            obj = CatalogProduct.objects.filter(name__iexact=eng_name).first()
            if not obj:
                skipped += 1  # allaqachon o'girilgan yoki mavjud emas
                continue
            obj.name = uz_name
            obj.description = uz_desc
            if not dry:
                obj.save(update_fields=['name', 'description', 'updated_at'])
            updated += 1

        mode = 'DRY-RUN (yozilmadi)' if dry else 'QO\'LLANDI'
        self.stdout.write(self.style.SUCCESS(
            f"[{mode}] o'girildi: {updated}, o'tkazildi (topilmadi/o'girilgan): {skipped}, "
            f"jami tarjima: {len(TRANSLATIONS)}"))
