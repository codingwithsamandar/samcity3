# PROMPT — SamCity: taksi va ko'p tillilikni arxivlash o'zgarishlarini birlashtirish

> Bu faylni Claude Code'ga to'g'ridan-to'g'ri bering: loyiha papkasida
> `claude` ni ishga tushirib, «PROMPT.md ni o'qi va bajar» deng.
> Fayl mustaqil ko'rsatma — oldingi suhbatni bilmasa ham ishlaydi.

---

## HOZIRGI HOLAT (avval shuni o'qi)

Loyihaga ALLAQACHON qo'llangan va diskda turgan o'zgarishlar — **ularga tegma,
qaytarma**:

- `assistant/tools/delivery.py` — AI orqali buyurtmada yetkazish manzili endi
  MAJBURIY (`propose_order(address=...)`), ilgari `address=''` yozilardi va
  kuryerga bo'sh manzil tushardi
- `assistant/tests/test_tools_delivery.py`, `assistant/tests/test_chain.py` —
  shu o'zgarishga moslangan + 2 ta regressiya testi
- `delivery/templates/delivery/driver_dashboard.html`,
  `delivery/templates/delivery/_driver_available.html`,
  `delivery/templatetags/delivery_extras.py` (yangi),
  `delivery/templatetags/__init__.py` (yangi) — kuryer panelida yetkazish
  manzili xaritada + «Yo'l ko'rsatish» navigator tugmasi

**Qo'llanmagan va SENING VAZIFANG** — `samcity_BARCHA_ozgarishlar.zip`
ichidagi 31 fayl (taksi + ko'p tillilik arxivi). Bu 31 faylning HECH BIRI
yuqoridagi ro'yxat bilan kesishmaydi, shuning uchun konflikt kutilmaydi.

---

## VAZIFA

`samcity_BARCHA_ozgarishlar.zip` ichidagi 31 ta tayyor faylni `merged_project`
loyihasiga birlashtir, keyin tekshir. O'zgarishlar ikki narsani **arxivlaydi**
(o'chirmaydi — flag bilan qaytariladi):

1. **Taksi moduli** — foydalanuvchi uchun butunlay yopiq (`TAXI_ENABLED=False`)
2. **Ko'p tillilik** — sayt faqat o'zbekchada (`MULTILANG_ENABLED=False`)

---

## LOYIHA KONTEKSTI

- **SamCity** — Django 5 (ASGI/Channels + DRF) + Flutter super-app, Shofirkon shahri uchun
- Loyiha: `C:\Users\user\Desktop\New folder\merged_project`
- Python **3.12+ shart** (kodda 3.12 f-string sintaksisi bor — 3.11 da `SyntaxError`)
- Django app'lar: `main delivery taxi payments booking notifications places api sms telegrambot assistant`
- `assistant` = "Jarvis" — LLM tool-calling agent (`assistant/tools/*.py` reyestri)
- `jarvis/` papkasi — **alohida desktop loyiha**, Django'ga aloqasi yo'q, tegilmasin
- Fayllarning aksari **CRLF** qatorlar oxiri bilan (Windows). ZIP ichida saqlangan.

---

## MUHIM: QANDAY BIRLASHTIRISH

O'zgarishlar diskdagi holat asosida (**2026-08-08**) tayyorlangan. Agar shundan
keyin o'sha fayllarni tahrirlagan bo'lsang — avval `git diff` bilan tekshir.

```bash
cd "C:\Users\user\Desktop\New folder\merged_project"
git status                       # nima o'zgargan
git stash list                   # kutilmagan narsa yo'qmi
git checkout -b arxiv/taxi-va-tillar
```

Keyin ZIP'ni loyiha ildiziga och (mavjud fayllar ustiga yozadi):

```bash
unzip -o samcity_BARCHA_ozgarishlar.zip -d .
```

`_arxiv/` papkasi — faqat **zaxira nusxa** (taxi moduli, api taxi fayllari,
`locale/en` va `locale/ru`). Loyihaga kerak emas, loyihadan tashqariga ko'chir
yoki o'chir:

```bash
mv _arxiv ../samcity_arxiv_2026-08-08
```

Keyin diffni ko'zdan kechir:

```bash
git diff --stat
git diff sdev/settings.py assistant/engine.py
```

---

## O'ZGARGAN FAYLLAR (31)

**Backend — flag va marshrutlar**

| Fayl | O'zgarish |
|---|---|
| `sdev/settings.py` | `TAXI_ENABLED = env_bool('TAXI_ENABLED', False)`; `MULTILANG_ENABLED = env_bool('MULTILANG_ENABLED', False)`; `LANGUAGES` flagga bog'landi; `TEMPLATES` ga `main.context_processors.feature_flags` qo'shildi |
| `sdev/urls.py` | `path('taxi/', ...)` faqat `TAXI_ENABLED` bo'lsa `urlpatterns` ga qo'shiladi |
| `sdev/asgi.py` | `import taxi.routing` shartli — `ws/taxi/...` ulanmaydi |
| `api/urls.py` | 3 router registratsiyasi + 5 path `if settings.TAXI_ENABLED:` blokiga o'tdi; `taxi_patterns` ro'yxati `*taxi_patterns` bilan yoyiladi |
| `main/context_processors.py` | **YANGI** — `feature_flags()`: `TAXI_ENABLED`, `MULTILANG_ENABLED`, `DELIVERY_CART_ENABLED` |
| `main/views.py` | dashboard konteksti: `trips` so'rovi flag o'chiq bo'lsa qilinmaydi |
| `places/views.py` | `_taxi_points()` flag o'chiq bo'lsa `[]` (xaritada taksist nuqtalari yo'q) |
| `notifications/signals.py` | `Trip` post_save receiver'i erta `return` (`reverse('taxi:...')` chaqirilmaydi) |

**Shablonlar**

| Fayl | O'zgarish |
|---|---|
| `main/templates/base.html` | navbar / mobil menyu / futerdagi taksi havolalari `{% if TAXI_ENABLED %}`; til almashtirgichning **ikkala** formasi `{% if MULTILANG_ENABLED %}` |
| `main/templates/home.html` | 2 ta taksi xizmat kartasi `{% if TAXI_ENABLED %}` |
| `main/templates/dashboard.html` | onboarding qadami + "Taksi sayohatlar" kartasi `{% if TAXI_ENABLED %}` |
| `main/static/manifest.json` | PWA `shortcuts` dan `/taxi/` olib tashlandi (3 → 2) |

**AI agent (Jarvis) — eng muhim qism**

> Taksi faqat sahifa/API'da emas, agentda ham **to'liq tool** edi
> (`assistant/tools/taxi.py`: `find_taxists`, `list_routes`, `propose_trip`,
> `create_trip`). Faqat URL'larni yopish yetarli EMAS edi.

| Fayl | O'zgarish |
|---|---|
| `assistant/tools/__init__.py` | `_enabled_modules()` — flag o'chiq bo'lsa `taxi` moduli **import qilinmaydi**, ya'ni `registry.build_llm_tools()` taxi bo'limini LLM sxemasiga qo'shmaydi |
| `assistant/tools/account.py` | `my_trips` amali flag o'chiq bo'lsa "xizmat o'chirilgan" deydi |
| `assistant/prompts.py` | `_strip_taxi(STATIC_PROMPT)` — import paytida **bir marta**, shuning uchun prompt bayt-ma-bayt barqaror qoladi (LLM prompt keshi buzilmaydi) |
| `assistant/engine.py` | `is_action_intent()` dan **oldin** taksi tekshiruvi → `intent='taxi_disabled'`, "🚧 Taksi xizmati hozircha o'chirilgan" javobi; keyingi TAXI branch faqat flag yoqilganda ishlaydi |
| `assistant/knowledge.py` | `TAXI_KB_IDS = ('order_taxi', 'become_taxist')`; `answer()` ularni chetlab o'tadi; `overview_actions()` dan taksi yorlig'i olindi |

**Seed va testlar**

| Fayl | O'zgarish |
|---|---|
| `main/management/commands/seed_all.py` | `seed_taxi` ro'yxatdan olindi |
| `main/management/commands/seed_demo_full.py` | `_seed_taxi()` va `_seed_taxi_trips()` flagga bog'landi |
| `taxi/tests.py` | `TaxistListTests`, `TripTests` → `@skipUnless(settings.TAXI_ENABLED, ...)` |
| `api/tests.py` | `TaxiAPITests` → `@skipUnless` |
| `api/test_taxist_panel.py` | `TaxistPanelTests` → `@skipUnless` |
| `assistant/tests/test_taxi.py` | 4 klass → `@skipUnless` |
| `assistant/tests/test_account.py` | `test_my_trips` → `@skipUnless` |
| `assistant/tests/test_engine.py` | `test_become_taxist`, `test_taxi_call_retreats_to_agent` → `@skipUnless`; **2 yangi test**: `test_taxi_kb_hidden_when_archived`, `test_taxi_requests_report_disabled` |

**Mobil (Flutter)**

| Fayl | O'zgarish |
|---|---|
| `mobile/lib/core/feature_flags.dart` | **YANGI** — `const kTaxiEnabled = bool.fromEnvironment('TAXI_ENABLED')` |
| `mobile/lib/core/router.dart` | `/taxist/:id`, `/trips`, `/taxist-panel` marshrutlari `if (kTaxiEnabled)` bilan — deep-link ham ochilmaydi |
| `mobile/lib/features/shell/home_shell.dart` | pastki navigatsiya statik 6 ta `NavigationDestination` o'rniga dinamik `_tabs` ro'yxati — Taksi tabi tushib qoladi, indekslar avtomatik siljiydi (`IndexedStack` ham `_tabs.length` ga bog'landi) |
| `mobile/lib/features/shell/more_services_screen.dart` | "Sayohatlarim" yozuvi `if (kTaxiEnabled)` (const collection-if) |
| `mobile/lib/features/profile/profile_screen.dart` | "Sayohatlarim (taksi)" va "Haydovchi paneli" `if (kTaxiEnabled) ...[ ]` spread bilan |

**Hujjat**

| Fayl | O'zgarish |
|---|---|
| `.env.example` | `TAXI_ENABLED=False` va `MULTILANG_ENABLED=False` + izohlar |

---

## ATAYLAB QILINMAGAN ISHLAR (o'zgartirma!)

1. **`taxi` app `INSTALLED_APPS` da QOLDI.** `delivery` va `payments` ning 7 ta
   shabloni `{% load taxi_extras %}` ishlatadi. App'ni olib tashlasang o'sha
   sahifalar `TemplateSyntaxError` beradi.
2. **`taxi/` papkasi o'chirilmadi**, migratsiyalar ham. Baza jadvallari va
   ma'lumot joyida.
3. **Baza tegilmadi** — hech qanday yangi migratsiya kerak emas.
4. **`locale/ru`, `locale/en`** `.po`/`.mo` fayllari joyida — flagni `True`
   qilsang uchala til qayta tarjimasiz qaytadi.
5. **Admin panel** — jazzmin ikonkalari va `order_with_respect_to` dagi `taxi`
   qoldi; staff arxivni ko'ra oladi. To'liq yashirish kerak bo'lsa
   `sdev/settings.py` dagi shu ikki joydan `taxi` ni olib tashlash yetarli.
6. **`.lang-switch` CSS** `base.html` da qoldi (forma yo'q, faqat uslub).
7. **`assistant/tts.py`** kirill matnga rus ovozini tanlaydi — bu interfeys tili
   emas, ovoz sintezi. Tegilmadi.
8. **`nginx.conf`, `entrypoint.sh`** — faqat izohlarda "taxi" so'zi bor, kodda emas.

---

## TEKSHIRISH (birlashtirgandan keyin SHART)

```bash
python -m venv venv && venv\Scripts\activate      # Python 3.12+
pip install -r requirements.txt
python manage.py check                            # 0 muammo bo'lishi kerak
python manage.py test                             # pastdagi izohga qara
```

Keyin quyidagi funksional tekshiruvni bajar (yoki `python manage.py shell` da
`django.test.Client` bilan qo'lda) — **hammasi shunday bo'lishi kerak**:

| Tekshiruv | Kutilgan |
|---|---|
| `GET /taxi/`, `/taxi/map/`, `/taxi/my-trips/`, `/taxi/taxist/register/` | `404` |
| `GET /`, `/delivery/`, `/map/`, `/payments/`, `/booking/` | `200` |
| `reverse('taxi:home')` | `NoReverseMatch` |
| `GET /api/taxi/taxists/`, `/api/taxi/trips/`, `/api/taxi/me/` | `404` |
| `GET /api/stores/` | `200` |
| `sdev.asgi.websocket_urlpatterns` | `taxi` yo'q |
| `registry.build_llm_tools()` bo'lim nomlari | `places, delivery, booking, ads, jobs, community, account` — **taxi yo'q** |
| `registry.dispatch('taxi', 'find_taxists', {}, ctx)` | `noma'lum tool` xatosi |
| `'• taxi' in prompts.STATIC_PROMPT` | `False` |
| `engine.handle("taksi chaqir")['intent']` | `'taxi_disabled'`, havolasiz |
| `places.views._taxi_points()` | `[]` |
| Bosh sahifa HTML: `name="language"`, `setlang`, `Русский`, `English` | har biri **0** marta |
| `POST /i18n/setlang/ {language: ru}` dan keyin bosh sahifa | `<html lang="uz">` |
| `Taxist.objects.count()` va `delivery/driver_dashboard.html` render | ishlaydi (arxiv o'qiladi) |

**Test to'plami haqida:** o'zgarishlar bulut sandbox'ida sinovdan o'tgan va
o'sha yerda **yangi yiqilish keltirmagan** (6 ta taksi-agent testi to'g'ri skip
bo'lgan). Lekin sandbox'dagi nusxa GitHub'ning eski `main` i bilan aralash edi,
shuning uchun u yerda 137 ta oldindan mavjud yiqilish bor edi. **Haqiqiy diskdagi
loyihada testlarni qaytadan ishga tushir** va natijani o'zgarishlardan
OLDINGI holat bilan solishtir:

```bash
git stash && python manage.py test 2>&1 | tail -3     # oldingi holat
git stash pop && python manage.py test 2>&1 | tail -3 # keyingi holat
```

Yangi yiqilish bo'lmasligi kerak; `skipped` soni ~33 ga oshadi.

---

## QAYTA YOQISH

`.env` ga yoz:

```env
TAXI_ENABLED=True
MULTILANG_ENABLED=True
```

Mobil ilova uchun alohida:

```bash
flutter build apk --release --dart-define=TAXI_ENABLED=true
```

Hech qanday migratsiya yoki tarjima qayta yig'ish kerak emas.

---

## AGAR KONFLIKT CHIQSA

ZIP'dagi fayllar **to'liq nusxa** (patch emas). Agar 2026-08-08 dan keyin o'sha
faylni tahrirlagan bo'lsang, ZIP versiyasi seniki ustiga yozadi. Shunday holatda:

1. `git diff HEAD~1 -- <fayl>` bilan ZIP nima o'zgartirganini ko'r
2. O'zgarish har doim aniq belgilangan: `TAXI_ENABLED` / `MULTILANG_ENABLED` /
   `kTaxiEnabled` so'zi bo'lgan qatorlar va ular ochgan `if` bloklari
3. Faqat o'sha bloklarni o'z versiyangga ko'chir

Qidirish uchun:

```bash
grep -rn "TAXI_ENABLED\|MULTILANG_ENABLED\|kTaxiEnabled\|TAXI_KB_IDS" --include="*.py" --include="*.html" --include="*.dart" .
```
