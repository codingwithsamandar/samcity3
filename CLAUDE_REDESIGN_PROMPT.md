# SamCity — UI/UX qayta dizayn topshirig'i (Claude Code uchun prompt)

## 1. Loyiha haqida qisqacha
Bu — Django asosidagi "SamCity" super-ilova: bitta shaharlik platforma ichida bir nechta modul bor:
- `main` — bosh sahifa, e'lonlar, ish (vakansiya/rezyume), transport, mahalla/community, profil, dashboard, auth
- `places` — joylar katalogi, xarita, nearby, sevimlilar
- `taxi` — taksi buyurtma, real-time tracking, haydovchi paneli
- `delivery` — do'konlar, mahsulotlar, savat, buyurtma tracking, haydovchi paneli
- `booking` — joy/venue bron qilish
- `payments` — to'lovlar, kvitansiyalar
- `notifications` — bildirishnomalar

Umumiy layout: `main/templates/base.html` (navbar, footer, mobile bottom-nav, barcha global CSS shu yerda inline yozilgan — `<style>` bloklari ko'p, ayrimlari bir-birini override qiladi). Qo'shimcha stil fayli: `main/static/css/samcity.css`. Har bir app o'z `templates/<app>/*.html` papkasida sahifalarga ega va barchasi `{% extends "base.html" %}` qiladi.

Diqqat: `.claude/worktrees/` ichida loyihaning boshqa (to'liqroq) nusxasi bor — masalan `delivery` app'ida asosiy joyda yo'q, lekin worktree'da mavjud sahifalar bor (`cart.html`, `checkout.html`, `product_detail.html`, `store_detail.html`, `driver_dashboard.html` va h.k.). Ishni boshlashdan oldin qaysi branch/worktree "haqiqiy joriy holat" ekanini aniqlashtir va shu asosda ishla.

## 2. Muammo — nega qayta dizayn kerak
Hozirgi dizayn "AI tomonidan generatsiya qilingan" degan taassurot qoldiradi va bachkana ko'rinadi. Aniq belgilari (`base.html` ichida topilgan):
- Fonda doimiy suzib yuruvchi rangli "aurora" bloblar (`.aurora-bg .a1/a2/a3/a4`, drift animatsiyalari)
- Hamma joyda ortiqcha glassmorphism/blur (`.glass`, `backdrop-filter: blur(16-22px)` deyarli har bir kartada)
- Sarlavhalarda rangli animatsion gradient matn (`.grad-anim`, `gradShift`)
- Kartalarda 3D tilt/glare, spotlight cursor-follow effektlari, sheen/shimmer tugmalar
- Floating card'lar, oltin rang pulsatsiyasi (`goldPulse`), scroll progress bar, "WOW layer" nomi bilan yozilgan bo'lim
- Emoji ikonlar interfeys ichida (📱, ☀️, 🌙) professional SVG ikon tizimi bor bo'lsa ham
- Bir nechta palitra/tema bloki bir-birini "consolidation" qilib ustma-ust yozilgan — bu kod ham, natija ham tartibsiz

Bularning barchasi generic AI-shablon dizaynlarga xos "premium effekt to'plami" hisoblanadi va zamonaviy, ishonchli mahsulot taassurotini bermaydi.

## 3. Maqsad
Butun frontendni professional darajadagi, o'ziga xos, "inson dizayner qilgan" his qiladigan darajaga olib chiqish:
- UI/UX 10/10: har bir foydalanuvchi istalgan sahifada "men qayerdaman, keyin nima qilishim kerak" degan savolga bir soniyada javob topa olishi kerak
- Zamonaviy, lekin jimjimasiz (minimal effekt, maqsadli animatsiya — dekorativ emas, funksional)
- Har bir modul (taksi, yetkazish, joylar, ish, e'lon, to'lov) o'z rangi/ikon ovozi bilan ajralib tursin, lekin yagona dizayn tizimi ichida
- Hech qanday "AI generated" taassurot qoldirmasin: aurora fon, rainbow gradient, ortiqcha glow/tilt/shimmer effektlar — barchasi olib tashlansin yoki juda minimal, maqsadga xizmat qiladigan darajaga tushirilsin

## 4. Qamrov — nima o'zgaradi, nima o'zgarmaydi

**O'ZGARMAYDI (tegilmang):**
- `main/templates/home.html` — bosh sahifa
- Barcha "yaratish/tahrirlash" formalari, ya'ni fayl nomida `_form`, `_edit`, `_create` bor sahifalar yoki create/edit vazifasini bajaradigan shablonlar. Masalan (ro'yxat to'liq emas, shunga o'xshaganlarning barchasi): `place_form.html`, `venue_create.html`, `job_form.html`, `resume_form.html`, `transport_form.html`, `utility_form.html`, `utility_edit.html`, `profile_edit.html`, `taxist_form.html`, `driver_register.html`, `product_form.html`, `store_form.html`.
  - Ishni boshlashdan oldin shu turdagi barcha shablonlarni ro'yxatlab chiq va menga tasdiqlash uchun ko'rsat (yoki aniq bir qoidaga rioya qil: nomi `_form`/`_edit`/`_create` bilan tugaydigan yoki asosiy vazifasi forma to'ldirish bo'lgan shablonlar — bularga tegma).

**O'ZGARADI (qayta dizayn qilinadi):**
- `main/templates/base.html` — navbar, footer, mobile bottom-nav, mobile drawer, global CSS/dizayn tizimi
- Qolgan barcha sahifalar: ro'yxatlar (`store_list`, `venue_list`, `job_list`, `place_list`, `resume_list`, `all_ads` va h.k.), detail sahifalari (`venue_detail`, `place_detail`, `job_detail`, `product_detail`, `store_detail`), dashboard va profil sahifalari, savat/checkout/buyurtma tracking, to'lov sahifalari, bildirishnomalar, mahalla/community, auth (login/register/OTP) sahifalari, confirm-delete sahifalari va boshqalar.

## 5. Navbar / axborot arxitekturasini qayta qurish
Hozirgi navbar tartibi: Bosh → E'lonlar → Ish → Taksi → To'lovlar → Joylar → Xarita → Yetkazish → Mahalla (9 ta band, mobil ekranda sig'maydi, burger menyuga tushib ketadi).

Talab: navbarni foydalanuvchi xulq-atvori va muhimlik darajasi bo'yicha qayta tuzish — masalan **Yetkazib berish (Yetkazish)** bo'limi eng ko'p ishlatiladigan/muhim xizmat bo'lsa, uni old qatorga chiqar. Buni shunchaki tartibni almashtirish bilan emas, quyidagicha yondashuv bilan hal qil:
1. Barcha bo'limlarni mantiqiy guruhlarga bo'l (masalan: "Xizmatlar" — Taksi/Yetkazish/Joylar/Bron; "Bozor" — E'lonlar/Ish; "Jamiyat" — Mahalla; alohida — Xarita, To'lovlar).
2. Eng ko'p ishlatiladigan 3–4 ta bo'limni to'g'ridan-to'g'ri navbarda ko'rinadigan qilib qoldir (shundan biri — Yetkazish, eng boshida yoki eng ko'zga tashlanadigan joyda), qolganlarini ochiladigan "Xizmatlar" / "Ko'proq" menyusiga joylashtir — 9 ta tekis link emas.
3. Mobil pastki navigatsiyani ham shu yangi ustuvorlikka moslab qayta tuzish (hozir: Bosh/E'lonlar/Ish/Xarita/Ko'proq — bu ham qayta ko'rib chiqilishi kerak, Yetkazish ko'rinmasligi mumkin emas agar u ustuvor xizmat bo'lsa).
4. Har bir sahifada joriy bo'lim navbarda aniq "active" holatda ko'rinishi, shuningdek chuqurroq sahifalarda breadcrumb yoki orqaga qaytish tugmasi bo'lishi kerak — foydalanuvchi hech qachon "qayerdaligini" yo'qotmasligi kerak.

## 6. Dizayn tamoyillari

**Olib tashlash / kamaytirish kerak bo'lganlar:**
- `.aurora-bg`, `.grain`, drift animatsiyalari — butunlay olib tashlansin
- Har bir kartadagi ortiqcha `backdrop-filter: blur()` glassmorphism — faqat maqsadli joylarda (masalan sticky navbar) qoldirilsin, kartalarda emas
- `.grad-anim`, animatsion rainbow gradient matnlar — statik, brendga mos 1–2 rangli aksent bilan almashtirilsin
- 3D tilt/glare/spotlight cursor-effektlari, shimmer/sheen tugma animatsiyalari, `goldPulse` kabi maqsadsiz pulsatsiyalar — olib tashlansin
- Emoji ikonlar (📱☀️🌙) — mavjud SVG ikon sprite (`#i-...`) bilan almashtirilsin, izchillik uchun

**Qo'shish / mustahkamlash kerak bo'lganlar:**
- Aniq, izchil dizayn tizimi: cheklangan rang palitrasi (1 asosiy aksent + neytral fon/matn ranglari + har modul uchun 1 ta farqlash rangi), tipografik shkala, spacing shkala, komponent kutubxonasi (tugmalar, kartalar, badge'lar, forma elementlari — hammasi bitta qoidaga bo'ysunsin)
- Har bir ro'yxat/detail sahifada aniq vizual ierarxiya: sarlavha → asosiy kontent → asosiy CTA har doim bir xil joyda va bir xil ko'rinishda
- Bo'sh holatlar (empty state), yuklanish holati (loading/skeleton), xato holati barcha sahifalarda izchil va tushunarli bo'lsin
- Real, funksional mikro-animatsiyalar (hover, focus, o'tish) — lekin dekorativ emas, 150–250ms, maqsadga xizmat qiluvchi
- Kontrast va o'qilishi (accessibility) — WCAG AA darajasida, dark/light ikkala temada ham
- Dark/light tema tizimi saqlanadi, lekin token tizimi soddalashtiriladi (hozir `:root` va `[data-theme="dark"]` bir necha marta ustma-ust "consolidated" deb yozilgan — buni bitta toza token to'plamiga tushir)

## 7. Texnik cheklovlar
- Django template sintaksisi (`{% url %}`, `{% block %}`, `{% include %}`, `{% if %}` va h.k.) buzilmasligi kerak — barcha URL nomlari, kontekst o'zgaruvchilari saqlanadi
- Mavjud funksionallik (savatga qo'shish, bildirishnoma bell, xarita integratsiyasi, real-time tracking JS, PWA install banner, tema almashtirish) ishlashda davom etishi kerak — faqat vizual/UX qatlami o'zgaradi, backend/JS logika buzilmasin (agar JS class nomlariga bog'liq bo'lsa, class nomini o'zgartirsang tegishli JS'ni ham yangila)
- CSS'ni bitta katta inline blokda emas, tartibli tashkil qil (masalan `main/static/css/samcity.css` ichida yagona, toza dizayn tizimi + har bir `<style>` blokni birlashtirib, bir-birini override qiluvchi eski qatlamlarni olib tashla)
- O'zgarishlarni kichik, ko'rib chiqsa bo'ladigan qadamlarda qil: avval dizayn tizimi/token'lar + navbar, keyin sahifa turkumlari bo'yicha (ro'yxatlar → detallar → dashboard/profil → savat/checkout → auth), har bosqichdan keyin natijani tekshir

## 8. Ish tartibi (tavsiya etilgan bosqichlar)
1. Loyihani branch/worktree holatini aniqlashtir (asosiy joriy holat qaysi — `.claude/worktrees` ichidagi versiyami yoki asosiy papkami), shundan keyin ishni boshla
2. Qamrovni aniqlashtir: qaysi shablonlar "forma/edit" toifasiga kirishini ro'yxatlab chiq va rioya qil
3. Yangi dizayn tizimini belgilash: rang palitrasi, tipografiya, spacing, komponentlar — bularni bitta joyda (masalan yangilangan `samcity.css`) hujjatlashtir
4. `base.html`: navbar/footer/mobile nav qayta qur (bo'lim 5 dagi IA asosida), aurora/glass/gradient-anim/tilt/emoji effektlarini olib tashla
5. Sahifalarni turkum-turkum qayta dizayn qil: ro'yxat sahifalari → detail sahifalari → dashboard/profil/bildirishnoma → savat/checkout/buyurtma tracking → to'lovlar → auth (login/register/OTP) → mahalla/community
6. Har bir modulni desktop va mobil ko'rinishda tekshir (responsive breakpoint'lar buzilmasligi kerak)
7. Oxirida: barcha sahifalarda navigatsiya izchilligini, active-state'larni, kontrastni va asosiy foydalanuvchi oqimlarini (masalan: bosh sahifa → yetkazish → mahsulot → savat → checkout) qo'lda sinovdan o'tkaz

## 9. Qabul qilish mezonlari
- Sahifada "aurora"/suzuvchi blob fon, rainbow animatsion gradient matn, emoji ikon, maqsadsiz tilt/glare/shimmer effekt qolmagan bo'lishi kerak
- Navbar 9 ta tekis link emas, ustuvorlik asosida guruhlangan va Yetkazish kabi muhim xizmat ko'rinadigan joyda bo'lishi kerak
- Har qanday sahifaga tasodifan tushib qolgan foydalanuvchi 3 soniya ichida "bu qaysi bo'lim, asosiy amal qayerda" ekanini tushuna olishi kerak
- Bosh sahifa va forma/edit sahifalari o'zgarishsiz qolgan bo'lishi kerak
- Barcha `{% url %}` havolalar va mavjud funksionallik ishlab turishi kerak (loyihani lokal ishga tushirib tekshirish tavsiya etiladi)
