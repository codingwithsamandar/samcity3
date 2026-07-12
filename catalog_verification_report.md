# Katalog tekshiruv hisoboti — Phase 3 (import OLDIDAN)

**Sana:** 2026-07-12 · **Manba:** `New/` (`catalog_150_products.json`, `catalog_images.zip`, `missing_images.json`) · **Nishon model:** `delivery.CatalogProduct` (migration `0018`)

> Bu hisobot faqat TEKSHIRUV natijasi. Hech narsa import qilinmadi, baza va kod o'zgartirilmadi.
> Raqamlar ikki bosqichda tasdiqlangan: deterministik skript + 3 ta mustaqil qayta-hisoblash agenti (adversarial verification).

---

## STEP 1 — Inspeksiya natijalari

| # | Ko'rsatkich | Natija |
|---|---|---|
| 1 | JSON'dagi mahsulotlar | **150** |
| 2 | Rasm fayllari (zip ichida) | **122** (barchasi `catalog/*.webp`) |
| 3 | Rasmi MAVJUD mahsulotlar | **122** |
| 4 | Rasmi YO'Q mahsulotlar | **28** (A ilova) |
| 5 | Mahsulotga bog'lanmagan (ortiqcha) rasmlar | **0** |
| 6 | Takroriy mahsulotlar (nom/slug bo'yicha) | **0** |
| 7 | Takroriy rasm fayl nomlari | **0** (zipda ham, JSON havolalarida ham) |
| 8 | Noto'g'ri kategoriyalar | **0** JSON ichida (har bir juftlik o'z daraxtida e'lon qilingan); lekin 9 kategoriya inglizcha va DB bilan MOS EMAS — mapping kerak (STEP 2) |
| 9 | Model tanlovlariga kirmaydigan birliklar | **8 xil birlik, 40 ta mahsulot**: jar(12), bar(8), can(6), bag(5), roll(3), loaf(2), bunch(2), tube(2) |
| 10 | Buzuq rasm havolalari | **0 buzuq fayl** (122/122 haqiqiy WEBP, PIL verify o'tdi, eng kattasi 92 KB ≪ 5MB limit). 28 ta havola faylga ega emas — bu №4 bilan bir xil ro'yxat |

Qo'shimcha tekshiruvlar:

- `missing_images.json` (28 ta deb da'vo qiladi) — **aniq mos**: nomma-nom bizning 28 talik ro'yxat bilan bir xil (slug yozilishi farq qiladi, xolos: `0-5l` vs `05l`).
- 14 ta mahsulotning `image_path`i Django `slugify(name)` qoidasidan chetlashadi — **zararsiz**: havola aniq ko'rsatilgan va fayl bor (yoki 28 talik ro'yxatda).
- Maydon sifati: nom ≤200 va brend ≤120 belgidan oshgani yo'q; bo'sh nom/brend/tavsif yo'q; barcha 150 yozuvda 7 kalit to'liq.
- `New/seed_catalog.py` **ISHLATIB BO'LMAYDI**: u boshqa sxema (`catalog.models.Category/Subcategory/Product`) uchun yozilgan — loyihada bunday app yo'q. Import uchun yangi `seed_catalog` buyrug'i `delivery.CatalogProduct`ga moslab yoziladi (Phase 4).
- `New/fetch_images.py` — rasmlarni yuklab olish uchun ishlatilgan yordamchi skript; importga aloqasi yo'q.

---

## STEP 2 — Moslik tekshiruvi (`delivery.CatalogProduct` bilan)

### 2.1 Maydon moslashuvi

| JSON maydoni | Model maydoni | Holat |
|---|---|---|
| `name` | `name` (≤200) | ✅ to'g'ridan-to'g'ri |
| `brand` | `brand` (≤120) | ✅ to'g'ridan-to'g'ri |
| `description` | `description` | ✅ to'g'ridan-to'g'ri |
| `unit` | `unit` (9 tanlov) | ⚠️ 40/150 mapping talab qiladi (2.2) |
| `category`+`subcategory` | `category` → `DeliveryCategory` FK | ⚠️ inglizcha taksonomiya ≠ DB; mapping talab qiladi (2.3). `subcategory` modelda YO'Q — u yo'qoladi (description'ga qo'shish mumkin) |
| `image_path` | `image` (ImageField) | ✅ `catalog/<slug>.webp` — media storagega yuklangach to'g'ridan-to'g'ri biriktiriladi; `.webp` validatorda ruxsat etilgan |
| — | `is_active` | default `True` |
| — | `created_by` | import qiluvchi admin |

### 2.2 Birlik (unit) mapping taklifi — 40 ta mahsulot

| JSON birlik | Soni | Taklif | Izoh |
|---|---|---|---|
| `jar` | 12 | → `piece` | banka (smetana, yogurt, murabbo...) |
| `bar` | 8 | → `piece` | plitka/batonchik (shokolad) |
| `can` | 6 | → `piece` | banka ichimlik (Red Bull...) |
| `bag` | 5 | → `pack` | qop (un, guruch) |
| `roll` | 3 | → `piece` | rulon (tualet qog'ozi...) |
| `loaf` | 2 | → `piece` | buxanka (non) |
| `bunch` | 2 | → `piece` | bog'lam (ko'katlar) |
| `tube` | 2 | → `piece` | tyubik (tish pastasi) |

Muqobil: `UNIT_CHOICES`ga shu 8 birlikni qo'shish (kod o'zgarishi + migratsiya kerak — hozircha taklif emas, MVP mapping bilan ketadi).

### 2.3 Kategoriya mapping taklifi (mavjud `DeliveryCategory` qatorlariga)

| JSON kategoriya | Mahsulot | Taklif → DeliveryCategory | DB'da bor? |
|---|---|---|---|
| Beverages | 20 | Ichimliklar (id=6) | ✅ |
| Fruits & Vegetables | 22 | Oziq-ovqat (id=1) | ✅ |
| Pantry & Groceries | 19 | Oziq-ovqat (id=1) | ✅ |
| Snacks & Confectionery | 18 | Oziq-ovqat (id=1) | ✅ |
| Dairy & Eggs | 15 | Oziq-ovqat (id=1) | ✅ |
| Bakery & Grains | 15 | Non mahsulotlari (id=5) | ✅ |
| Meat & Fish | 12 | Oziq-ovqat (id=1) | ✅ |
| Personal Care (Baby Care'dan tashqari) | 11 | Go'zallik (id=8) | ✅ |
| Personal Care → Baby Care | 3 | Bolalar (id=9) | ✅ |
| Household | 15 | **MOS YO'Q — QAROR KERAK** (C ilova) | ❌ |

`Household` (15 ta) uchun variantlar: (a) yangi `DeliveryCategory` "Uy-ro'zg'or" yaratish (import bosqichida, 1 qator); (b) `category=NULL` qoldirish (model ruxsat beradi); (c) mavjud kategoriyaga majburan biriktirish (tavsiya etilmaydi).

### 2.4 Mavjud ma'lumot bilan to'qnashuv

Bazada allaqachon 3 ta `CatalogProduct` bor (Phase 2 sinovidan): `Sut 1L`, `Non (tandir)`, `Tuxum 10 dona`. JSON'dagi 150 nom bilan **to'qnashuv yo'q** (JSON inglizcha nomlar). Eslatma: `UHT Milk 3.2% 1L` va `Sut 1L` mantiqan yaqin — import forma nomlari inglizcha bo'lgani uchun dublikat hisoblanmaydi; nomlarni o'zbekchalashtirish alohida qaror (quyida, Tavsiyalar).

---

## STEP 3 — Import simulyatsiyasi (dry run — hech narsa yozilmadi)

Barcha 150 mahsulot nom bo'yicha unikal va DB bilan to'qnashmaydi, shuning uchun **SKIP = 0**.

| Toifa | Soni | Izoh |
|---|---|---|
| ✅ TOZA yaratiladi (hech qanday ogohlantirishsiz) | **75** | birlik mos, rasm bor, kategoriya avtomatik |
| 🔧 Birlik mapping bilan yaratiladi | **40** | 2.2 jadval tasdiqlansa avtomatik (B ilova) |
| 🖼️ Rasmsiz yaratiladi | **28** | `image=NULL` (maydon ixtiyoriy); rasm keyin qo'shiladi (A ilova) |
| ⏸️ QO'LDA QAROR kerak | **15** | faqat `Household` kategoriyasi savoli (C ilova) |
| ⛔ SKIP (dublikat/to'qnashuv) | **0** | |

Kesishmalar (bir mahsulot bir nechta toifada bo'lishi mumkin): birlik∩rasmsiz=5, birlik∩household=3, rasmsiz∩household=0.

**Xulosa:** 2.2 (birlik map) va "rasmsiz import OK" tasdiqlansa — **135/150** darhol import qilinadi; qolgan **15** (`Household`) faqat kategoriya qarorini kutadi. To'liq 150 tasi ham import qilinishi mumkin — bitta qaror bilan.

### Import oldidan hal qilinishi kerak (Phase 4 kirishi)

1. **Household kategoriyasi**: yangi "Uy-ro'zg'or" yaratilsinmi, NULL qoldirilsinmi?
2. **Birlik mappingi** (2.2) tasdiqlanadimi, yoki `UNIT_CHOICES` kengaytirilsinmi (migratsiya)?
3. **28 rasmsiz mahsulot**: rasmsiz import qilinsinmi (tavsiya) yoki rasmlar topilguncha kutilsinmi?
4. **Nomlar/tavsiflar inglizcha** — sayt o'zbek tilida. Import asl holicha qilinib keyin tarjima qilinadimi, yoki oldin tarjima? (150 nom + 150 tavsif)
5. **Media storage**: productionda rasmlar Supabase S3'ga yuklanishi kerak (lokalda `media/catalog/`ga unzip yetarli emas) — import buyrug'i storage API orqali yozishi kerak.

### Tavsiyalar

- `New/seed_catalog.py`ni ishlatmang — sxemasi boshqa. Phase 4'da `delivery/management/commands/seed_catalog.py` yoziladi: idempotent (nom bo'yicha update_or_create), `--dry-run` bayrog'i, unit/kategoriya mappingi shu hisobotdagidek.
- `subcategory` ma'lumotini yo'qotmaslik uchun description oxiriga yoki keyinchalik teg sifatida saqlashni ko'rib chiqing.
- Import test bazada avval sinab ko'riladi, keyin productionga.
- ⚠️ Diqqat: noto'g'ri birliklar (`jar` va h.k.) `unit` maydoniga SIG'ADI (max_length=10) — `bulk_create` ularni jimgina saqlab yuboradi va tanlov ro'yxatidan tashqarida qoladi. Import buyrug'i har bir yozuvda `full_clean()` chaqirishi yoki mappingni majburiy qo'llashi SHART.

---

## A ilova — Rasmsiz 28 mahsulot (rasmsiz import qilinadi)

- Hydrolife Still Water 1.5L  (Beverages / Water)
- Chortoq Mineral Water 1L  (Beverages / Water)
- Piko Apple Juice 1L  (Beverages / Juices & Nectars)
- Piko Peach Nectar 1L  (Beverages / Juices & Nectars)
- Piko Tomato Juice 1L  (Beverages / Juices & Nectars)
- Adrenaline Rush Energy Drink 0.5L  (Beverages / Energy Drinks)
- UHT Milk 3.2% 1L  (Dairy & Eggs / Milk)
- Hochland Cream Cheese 180g  (Dairy & Eggs / Cheese & Butter)
- Suluguni Cheese 300g  (Dairy & Eggs / Cheese & Butter)
- Chicken Eggs C0 30 pcs  (Dairy & Eggs / Eggs)
- Obi Non Flatbread  (Bakery & Grains / Bread & Non)
- Patyr Non Flatbread  (Bakery & Grains / Bread & Non)
- Wheat Flour Premium 2kg  (Bakery & Grains / Flour & Baking)
- Saf-Moment Dry Yeast 11g  (Bakery & Grains / Flour & Baking)
- Makfa Spaghetti 450g  (Bakery & Grains / Pasta & Noodles)
- Doshirak Instant Noodles Chicken 90g  (Bakery & Grains / Pasta & Noodles)
- Devzira Rice 1kg  (Bakery & Grains / Rice & Grains)
- Ground Beef 500g  (Meat & Fish / Beef & Lamb)
- Husayni Grapes 1kg  (Fruits & Vegetables / Fresh Fruits)
- Walnut Kernels 300g  (Fruits & Vegetables / Dried Fruits & Nuts)
- Oleina Sunflower Oil 1L  (Pantry & Groceries / Oils)
- Cumin Seeds (Zira) 50g  (Pantry & Groceries / Sugar, Salt & Spices)
- Chili Adjika Sauce 300g  (Pantry & Groceries / Sauces & Condiments)
- Alpen Gold Hazelnut Chocolate 85g  (Snacks & Confectionery / Chocolate & Candy)
- Yubileynoye Cookies 112g  (Snacks & Confectionery / Cookies & Wafers)
- Barni Sponge Cake 30g  (Snacks & Confectionery / Cookies & Wafers)
- Vanilla Plombir Ice Cream 400g  (Snacks & Confectionery / Ice Cream)
- Schauma Shampoo 400ml  (Personal Care / Hair Care)

## B ilova — Birlik mappingi bilan 40 mahsulot

**`jar` → `piece`** (12):
- Nescafe Classic Instant Coffee 190g
- Qatiq 3.2% 500g
- Suzma 400g
- Sour Cream 20% 400g
- Activia Natural Yogurt 290g
- Strawberry Yogurt 290g
- Tomato Paste 500g
- Pickled Cucumbers 900g
- Mayonnaise 67% 400g
- Chili Adjika Sauce 300g
- Natural Honey 500g
- Nivea Soft Cream 75ml

**`bar` → `piece`** (8):
- Snickers Bar 50g
- Mars Bar 51g
- Twix Bar 55g
- Milka Alpine Milk Chocolate 90g
- Alpen Gold Hazelnut Chocolate 85g
- KitKat 4 Fingers 41g
- Dove Beauty Bar 100g
- Safeguard Soap 90g

**`can` → `piece`** (6):
- Red Bull Energy Drink 250ml
- Adrenaline Rush Energy Drink 0.5L
- Canned Tuna in Oil 185g
- Canned Green Peas 400g
- Condensed Milk 380g
- Rexona Deodorant Spray 150ml

**`bag` → `pack`** (5):
- Wheat Flour Premium 2kg
- Devzira Rice 1kg
- Lazer Rice 1kg
- Buckwheat Groats 800g
- Granulated Sugar 1kg

**`roll` → `piece`** (3):
- Garbage Bags 30L 20 pcs
- Aluminium Foil 10m
- Cling Film 30m

**`loaf` → `piece`** (2):
- Sliced White Bread 500g
- Rye Bread 400g

**`bunch` → `piece`** (2):
- Fresh Dill
- Fresh Cilantro

**`tube` → `piece`** (2):
- Colgate Toothpaste 100ml
- Sensodyne Toothpaste 75ml

## C ilova — `Household` 15 mahsulot (kategoriya qarori kutilmoqda)

- Fairy Dishwashing Liquid 900ml  (Cleaning)
- Domestos Bleach 1L  (Cleaning)
- Glass Cleaner Spray 500ml  (Cleaning)
- Floor Cleaner 1L  (Cleaning)
- Kitchen Sponges 5 pcs  (Cleaning)
- Ariel Washing Powder 3kg  (Laundry)
- Tide Washing Powder 3kg  (Laundry)
- Persil Liquid Detergent 1.3L  (Laundry)
- Lenor Fabric Softener 1L  (Laundry)
- Toilet Paper 8 Rolls  (Paper Goods)
- Paper Towels 2 Rolls  (Paper Goods)
- Paper Napkins 100 pcs  (Paper Goods)
- Garbage Bags 30L 20 pcs  (Kitchen Supplies)
- Aluminium Foil 10m  (Kitchen Supplies)
- Cling Film 30m  (Kitchen Supplies)

## D ilova — To'liq import ko'rinishi (150 qator)

`unit` ustunida `a→b` — mapping qo'llanadi; `Rasm` ❌ — rasmsiz import; `Kategoriya` **QAROR** — Household.

| # | Nomi | Brend | Birlik | Kategoriya (JSON → DB) | Rasm |
|---|---|---|---|---|---|
| 1 | Coca-Cola 1L | Coca-Cola | bottle | Beverages → Ichimliklar | ✅ |
| 2 | Coca-Cola Zero 0.5L | Coca-Cola | bottle | Beverages → Ichimliklar | ✅ |
| 3 | Fanta Orange 1L | Fanta | bottle | Beverages → Ichimliklar | ✅ |
| 4 | Sprite 1L | Sprite | bottle | Beverages → Ichimliklar | ✅ |
| 5 | Pepsi 1.5L | Pepsi | bottle | Beverages → Ichimliklar | ✅ |
| 6 | Mirinda Orange 1L | Mirinda | bottle | Beverages → Ichimliklar | ✅ |
| 7 | 7UP 1L | 7UP | bottle | Beverages → Ichimliklar | ✅ |
| 8 | Hydrolife Still Water 1.5L | Hydrolife | bottle | Beverages → Ichimliklar | ❌ |
| 9 | Chortoq Mineral Water 1L | Chortoq | bottle | Beverages → Ichimliklar | ❌ |
| 10 | Nestle Pure Life Water 5L | Nestle Pure Life | bottle | Beverages → Ichimliklar | ✅ |
| 11 | Piko Apple Juice 1L | Piko | box | Beverages → Ichimliklar | ❌ |
| 12 | Piko Peach Nectar 1L | Piko | box | Beverages → Ichimliklar | ❌ |
| 13 | Piko Tomato Juice 1L | Piko | box | Beverages → Ichimliklar | ❌ |
| 14 | Rich Orange Juice 1L | Rich | box | Beverages → Ichimliklar | ✅ |
| 15 | Lipton Yellow Label Tea 100 Bags | Lipton | pack | Beverages → Ichimliklar | ✅ |
| 16 | Ahmad Tea Green Tea 100g | Ahmad Tea | pack | Beverages → Ichimliklar | ✅ |
| 17 | Nescafe Classic Instant Coffee 190g | Nescafe | jar→piece | Beverages → Ichimliklar | ✅ |
| 18 | Jacobs Monarch Ground Coffee 250g | Jacobs | pack | Beverages → Ichimliklar | ✅ |
| 19 | Red Bull Energy Drink 250ml | Red Bull | can→piece | Beverages → Ichimliklar | ✅ |
| 20 | Adrenaline Rush Energy Drink 0.5L | Adrenaline Rush | can→piece | Beverages → Ichimliklar | ❌ |
| 21 | Pasteurized Milk 2.5% 1L | SamCity | bottle | Dairy & Eggs → Oziq-ovqat | ✅ |
| 22 | UHT Milk 3.2% 1L | SamCity | box | Dairy & Eggs → Oziq-ovqat | ❌ |
| 23 | Nesquik Chocolate Milk 200ml | Nesquik | box | Dairy & Eggs → Oziq-ovqat | ✅ |
| 24 | Kefir 2.5% 500ml | SamCity | bottle | Dairy & Eggs → Oziq-ovqat | ✅ |
| 25 | Qatiq 3.2% 500g | SamCity | jar→piece | Dairy & Eggs → Oziq-ovqat | ✅ |
| 26 | Ayran 0.5L | SamCity | bottle | Dairy & Eggs → Oziq-ovqat | ✅ |
| 27 | Suzma 400g | SamCity | jar→piece | Dairy & Eggs → Oziq-ovqat | ✅ |
| 28 | Sour Cream 20% 400g | SamCity | jar→piece | Dairy & Eggs → Oziq-ovqat | ✅ |
| 29 | Activia Natural Yogurt 290g | Activia | jar→piece | Dairy & Eggs → Oziq-ovqat | ✅ |
| 30 | Strawberry Yogurt 290g | SamCity | jar→piece | Dairy & Eggs → Oziq-ovqat | ✅ |
| 31 | Butter 82.5% 200g | SamCity | pack | Dairy & Eggs → Oziq-ovqat | ✅ |
| 32 | Hochland Cream Cheese 180g | Hochland | pack | Dairy & Eggs → Oziq-ovqat | ❌ |
| 33 | Suluguni Cheese 300g | SamCity | pack | Dairy & Eggs → Oziq-ovqat | ❌ |
| 34 | Chicken Eggs C1 10 pcs | Local Farm | tray | Dairy & Eggs → Oziq-ovqat | ✅ |
| 35 | Chicken Eggs C0 30 pcs | Local Farm | tray | Dairy & Eggs → Oziq-ovqat | ❌ |
| 36 | Obi Non Flatbread | Local Bakery | piece | Bakery & Grains → Non mahsulotlari | ❌ |
| 37 | Patyr Non Flatbread | Local Bakery | piece | Bakery & Grains → Non mahsulotlari | ❌ |
| 38 | Sliced White Bread 500g | SamCity | loaf→piece | Bakery & Grains → Non mahsulotlari | ✅ |
| 39 | Rye Bread 400g | SamCity | loaf→piece | Bakery & Grains → Non mahsulotlari | ✅ |
| 40 | Lavash Thin Flatbread 200g | Local Bakery | pack | Bakery & Grains → Non mahsulotlari | ✅ |
| 41 | Wheat Flour Premium 2kg | SamCity | bag→pack | Bakery & Grains → Non mahsulotlari | ❌ |
| 42 | Dr. Oetker Baking Powder 10g | Dr. Oetker | pack | Bakery & Grains → Non mahsulotlari | ✅ |
| 43 | Saf-Moment Dry Yeast 11g | Saf-Moment | pack | Bakery & Grains → Non mahsulotlari | ❌ |
| 44 | Makfa Spaghetti 450g | Makfa | pack | Bakery & Grains → Non mahsulotlari | ❌ |
| 45 | Vermicelli 400g | SamCity | pack | Bakery & Grains → Non mahsulotlari | ✅ |
| 46 | Doshirak Instant Noodles Chicken 90g | Doshirak | pack | Bakery & Grains → Non mahsulotlari | ❌ |
| 47 | Devzira Rice 1kg | Local Farm | bag→pack | Bakery & Grains → Non mahsulotlari | ❌ |
| 48 | Lazer Rice 1kg | Local Farm | bag→pack | Bakery & Grains → Non mahsulotlari | ✅ |
| 49 | Buckwheat Groats 800g | SamCity | bag→pack | Bakery & Grains → Non mahsulotlari | ✅ |
| 50 | Oat Flakes 500g | SamCity | pack | Bakery & Grains → Non mahsulotlari | ✅ |
| 51 | Beef Tenderloin 1kg | Local Farm | kg | Meat & Fish → Oziq-ovqat | ✅ |
| 52 | Ground Beef 500g | SamCity | pack | Meat & Fish → Oziq-ovqat | ❌ |
| 53 | Lamb Ribs 1kg | Local Farm | kg | Meat & Fish → Oziq-ovqat | ✅ |
| 54 | Whole Chicken 1.5kg | Local Farm | piece | Meat & Fish → Oziq-ovqat | ✅ |
| 55 | Chicken Fillet 1kg | Local Farm | kg | Meat & Fish → Oziq-ovqat | ✅ |
| 56 | Chicken Drumsticks 1kg | Local Farm | kg | Meat & Fish → Oziq-ovqat | ✅ |
| 57 | Doctor's Boiled Sausage 500g | SamCity | pack | Meat & Fish → Oziq-ovqat | ✅ |
| 58 | Beef Sausages 400g | SamCity | pack | Meat & Fish → Oziq-ovqat | ✅ |
| 59 | Kazi Horse Sausage 300g | Local Farm | pack | Meat & Fish → Oziq-ovqat | ✅ |
| 60 | Smoked Beef Salami 300g | SamCity | pack | Meat & Fish → Oziq-ovqat | ✅ |
| 61 | Frozen Mackerel 1kg | SamCity | kg | Meat & Fish → Oziq-ovqat | ✅ |
| 62 | Canned Tuna in Oil 185g | SamCity | can→piece | Meat & Fish → Oziq-ovqat | ✅ |
| 63 | Golden Apples 1kg | Local Farm | kg | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 64 | Bananas 1kg | Local Farm | kg | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 65 | Oranges 1kg | Local Farm | kg | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 66 | Husayni Grapes 1kg | Local Farm | kg | Fruits & Vegetables → Oziq-ovqat | ❌ |
| 67 | Watermelon | Local Farm | piece | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 68 | Mirzachul Melon | Local Farm | piece | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 69 | Pomegranate 1kg | Local Farm | kg | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 70 | Lemons 500g | Local Farm | kg | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 71 | Potatoes 1kg | Local Farm | kg | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 72 | Onions 1kg | Local Farm | kg | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 73 | Carrots 1kg | Local Farm | kg | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 74 | Tomatoes 1kg | Local Farm | kg | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 75 | Cucumbers 1kg | Local Farm | kg | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 76 | Bell Peppers 500g | Local Farm | kg | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 77 | White Cabbage | Local Farm | piece | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 78 | Garlic 200g | Local Farm | pack | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 79 | Fresh Dill | Local Farm | bunch→piece | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 80 | Fresh Cilantro | Local Farm | bunch→piece | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 81 | Raisins 500g | SamCity | pack | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 82 | Dried Apricots 500g | SamCity | pack | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 83 | Walnut Kernels 300g | SamCity | pack | Fruits & Vegetables → Oziq-ovqat | ❌ |
| 84 | Salted Peanuts 200g | SamCity | pack | Fruits & Vegetables → Oziq-ovqat | ✅ |
| 85 | Oleina Sunflower Oil 1L | Oleina | bottle | Pantry & Groceries → Oziq-ovqat | ❌ |
| 86 | Sunflower Oil 5L | SamCity | bottle | Pantry & Groceries → Oziq-ovqat | ✅ |
| 87 | Cottonseed Oil 1L | SamCity | bottle | Pantry & Groceries → Oziq-ovqat | ✅ |
| 88 | Borges Olive Oil 500ml | Borges | bottle | Pantry & Groceries → Oziq-ovqat | ✅ |
| 89 | Granulated Sugar 1kg | SamCity | bag→pack | Pantry & Groceries → Oziq-ovqat | ✅ |
| 90 | Iodized Salt 1kg | SamCity | pack | Pantry & Groceries → Oziq-ovqat | ✅ |
| 91 | Ground Black Pepper 50g | SamCity | pack | Pantry & Groceries → Oziq-ovqat | ✅ |
| 92 | Cumin Seeds (Zira) 50g | SamCity | pack | Pantry & Groceries → Oziq-ovqat | ❌ |
| 93 | Paprika Powder 50g | SamCity | pack | Pantry & Groceries → Oziq-ovqat | ✅ |
| 94 | Canned Green Peas 400g | SamCity | can→piece | Pantry & Groceries → Oziq-ovqat | ✅ |
| 95 | Tomato Paste 500g | SamCity | jar→piece | Pantry & Groceries → Oziq-ovqat | ✅ |
| 96 | Pickled Cucumbers 900g | SamCity | jar→piece | Pantry & Groceries → Oziq-ovqat | ✅ |
| 97 | Condensed Milk 380g | SamCity | can→piece | Pantry & Groceries → Oziq-ovqat | ✅ |
| 98 | Heinz Ketchup 350g | Heinz | bottle | Pantry & Groceries → Oziq-ovqat | ✅ |
| 99 | Mayonnaise 67% 400g | Mr. Ricco | jar→piece | Pantry & Groceries → Oziq-ovqat | ✅ |
| 100 | Soy Sauce 200ml | Sen Soy | bottle | Pantry & Groceries → Oziq-ovqat | ✅ |
| 101 | Table Vinegar 9% 500ml | SamCity | bottle | Pantry & Groceries → Oziq-ovqat | ✅ |
| 102 | Chili Adjika Sauce 300g | SamCity | jar→piece | Pantry & Groceries → Oziq-ovqat | ❌ |
| 103 | Natural Honey 500g | Local Farm | jar→piece | Pantry & Groceries → Oziq-ovqat | ✅ |
| 104 | Snickers Bar 50g | Snickers | bar→piece | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 105 | Mars Bar 51g | Mars | bar→piece | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 106 | Twix Bar 55g | Twix | bar→piece | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 107 | Milka Alpine Milk Chocolate 90g | Milka | bar→piece | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 108 | Alpen Gold Hazelnut Chocolate 85g | Alpen Gold | bar→piece | Snacks & Confectionery → Oziq-ovqat | ❌ |
| 109 | KitKat 4 Fingers 41g | KitKat | bar→piece | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 110 | Sunflower Halva 350g | SamCity | pack | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 111 | Oreo Cookies 95g | Oreo | pack | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 112 | Yubileynoye Cookies 112g | Yubileynoye | pack | Snacks & Confectionery → Oziq-ovqat | ❌ |
| 113 | Barni Sponge Cake 30g | Barni | piece | Snacks & Confectionery → Oziq-ovqat | ❌ |
| 114 | Chocolate Wafers 220g | SamCity | pack | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 115 | Salted Crackers 180g | SamCity | pack | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 116 | Lay's Classic Chips 80g | Lay's | pack | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 117 | Lay's Sour Cream & Onion 80g | Lay's | pack | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 118 | Pringles Original 165g | Pringles | box | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 119 | Salted Popcorn 100g | SamCity | pack | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 120 | Vanilla Plombir Ice Cream 400g | SamCity | box | Snacks & Confectionery → Oziq-ovqat | ❌ |
| 121 | Chocolate Ice Cream Cone 100g | SamCity | piece | Snacks & Confectionery → Oziq-ovqat | ✅ |
| 122 | Fairy Dishwashing Liquid 900ml | Fairy | bottle | Household → **QAROR** | ✅ |
| 123 | Domestos Bleach 1L | Domestos | bottle | Household → **QAROR** | ✅ |
| 124 | Glass Cleaner Spray 500ml | SamCity | bottle | Household → **QAROR** | ✅ |
| 125 | Floor Cleaner 1L | SamCity | bottle | Household → **QAROR** | ✅ |
| 126 | Kitchen Sponges 5 pcs | SamCity | pack | Household → **QAROR** | ✅ |
| 127 | Ariel Washing Powder 3kg | Ariel | pack | Household → **QAROR** | ✅ |
| 128 | Tide Washing Powder 3kg | Tide | pack | Household → **QAROR** | ✅ |
| 129 | Persil Liquid Detergent 1.3L | Persil | bottle | Household → **QAROR** | ✅ |
| 130 | Lenor Fabric Softener 1L | Lenor | bottle | Household → **QAROR** | ✅ |
| 131 | Toilet Paper 8 Rolls | SamCity | pack | Household → **QAROR** | ✅ |
| 132 | Paper Towels 2 Rolls | SamCity | pack | Household → **QAROR** | ✅ |
| 133 | Paper Napkins 100 pcs | SamCity | pack | Household → **QAROR** | ✅ |
| 134 | Garbage Bags 30L 20 pcs | SamCity | roll→piece | Household → **QAROR** | ✅ |
| 135 | Aluminium Foil 10m | SamCity | roll→piece | Household → **QAROR** | ✅ |
| 136 | Cling Film 30m | SamCity | roll→piece | Household → **QAROR** | ✅ |
| 137 | Head & Shoulders Shampoo 400ml | Head & Shoulders | bottle | Personal Care → Go'zallik | ✅ |
| 138 | Pantene Pro-V Shampoo 400ml | Pantene | bottle | Personal Care → Go'zallik | ✅ |
| 139 | Schauma Shampoo 400ml | Schauma | bottle | Personal Care → Go'zallik | ❌ |
| 140 | Colgate Toothpaste 100ml | Colgate | tube→piece | Personal Care → Go'zallik | ✅ |
| 141 | Sensodyne Toothpaste 75ml | Sensodyne | tube→piece | Personal Care → Go'zallik | ✅ |
| 142 | Toothbrush Medium | Colgate | piece | Personal Care → Go'zallik | ✅ |
| 143 | Dove Beauty Bar 100g | Dove | bar→piece | Personal Care → Go'zallik | ✅ |
| 144 | Safeguard Soap 90g | Safeguard | bar→piece | Personal Care → Go'zallik | ✅ |
| 145 | Nivea Soft Cream 75ml | Nivea | jar→piece | Personal Care → Go'zallik | ✅ |
| 146 | Rexona Deodorant Spray 150ml | Rexona | can→piece | Personal Care → Go'zallik | ✅ |
| 147 | Gillette Razor 3 Blades | Gillette | piece | Personal Care → Go'zallik | ✅ |
| 148 | Pampers Diapers Size 4 58 pcs | Pampers | pack | Personal Care → Bolalar | ✅ |
| 149 | Baby Wet Wipes 72 pcs | Pampers | pack | Personal Care → Bolalar | ✅ |
| 150 | Baby Shampoo 200ml | Johnson's | bottle | Personal Care → Bolalar | ✅ |

---
*Hisobot Phase 3 doirasida yaratildi. Baza, kod va migratsiyalarga TEGILMADI. Import Phase 4 tasdig'ini kutmoqda.*
