# SamCity — Render production media audit

> Sana: 2026-07-13 · Usul: kod tahlili + jonli production probe'lari
> (samcity.onrender.com + Supabase storage endpoint). **Kod o'zgartirilmagan.**

---

## 0. Xulosa (root cause) — bitta gapda

**Production shu paytgacha ESKI kodda ishlab kelgan (`d2e7efc`), unda
`AWS_DEFAULT_ACL = 'public-read'` — Supabase S3 API buni RAD ETADI, shuning
uchun HAR BIR yuklash PutObject bosqichida xato bergan va fayl UMUMAN
SAQLANMAGAN.** Tuzatish (`9828879`, 2026-07-12) master'da bor edi, lekin
Render deploy qiladigan `main` branchga bugungacha push qilinmagan.

Diagnoz turi: **(a) "not saved at all"** — fayllar yo'qolmayapti, ular
boshidanoq saqlanmayapti.

---

## 1. settings.py tahlili (joriy kod — tuzatilgan versiya)

`sdev/settings.py:234–306`:

| Sozlama | Qiymat | Baho |
|---------|--------|------|
| `MEDIA_URL` (default) | `/media/` | Lokal dev uchun |
| `MEDIA_ROOT` | `BASE_DIR/media` | Lokal dev uchun |
| `STORAGES['default']` | `AWS_STORAGE_BUCKET_NAME` bo'lsa → `S3Boto3Storage` | ✅ To'g'ri |
| `AWS_DEFAULT_ACL` | env yoki **None** (settings.py:285) | ✅ Supabase uchun SHART |
| `AWS_S3_ADDRESSING_STYLE` | `path` (settings.py:292) | ✅ Supabase virtual-host'ni qo'llamaydi |
| `AWS_S3_SIGNATURE_VERSION` | `s3v4` | ✅ |
| `AWS_QUERYSTRING_AUTH` | `False` | ✅ Public bucket uchun to'g'ri |
| `MEDIA_URL` (Supabase) | `https://shyllblzdbjctcbwgzun.storage.supabase.co/storage/v1/object/public/media/` | ✅ Host jonli tekshirildi (2-bo'lim) |
| Kalitlar bo'sh bo'lsa | stderr'ga ochiq `[media] OGOHLANTIRISH` (settings.py:269) | ✅ Render logda ko'rinadi |

**ESKI kod (production'da ishlab turgani, `d2e7efc`) bilan farq:**

```diff
-    AWS_DEFAULT_ACL = 'public-read'      # ← Supabase PutObject'ni buzadi
+    AWS_DEFAULT_ACL = env yoki None      # ← tuzatilgan (9828879)
```

Supabase S3-mos API obyekt ACL'larini (x-amz-acl) qo'llab-quvvatlamaydi —
`public-read` yuborilsa PutObject xato qaytaradi → Django exception → 500 →
na fayl, na DB yozuvi saqlanadi. Bu kod izohida ham hujjatlashtirilgan
(settings.py:280–284).

## 2. Yuklangan rasm URL tuzilmasi

Yangi kod Supabase uchun quyidagicha URL yasaydi:

```
https://shyllblzdbjctcbwgzun.storage.supabase.co/storage/v1/object/public/media/<path>
```

Jonli probe natijalari (2026-07-13):

| So'rov | Natija | Ma'nosi |
|--------|--------|---------|
| `GET .../object/public/media/test.jpg` | 404 `{"error":"not_found","message":"Object not found"}` | Host+route ISHLAYDI, obyekt yo'q |
| `GET .../object/public/nosuchbucket/x.jpg` | 404 `{"error":"Bucket not found"}` | Farqli xato → **`media` bucket MAVJUD** |
| `<ref>.supabase.co` va `<ref>.storage.supabase.co` | ikkalasi ham bir xil javob | Ikkala host varianti ham to'g'ri routelaydi |

Xulosa: URL sxemasi to'g'ri; bucket bor; **lekin ichida birorta ham obyekt
topilmadi** (katalog rasmi yo'lini ham tekshirdim — yo'q).

## 3. Django admin / DB'dagi yuklangan fayllar (production holati)

Ochiq API orqali tekshirildi (o'zgartirishsiz, faqat o'qish):

| Tekshiruv | Natija |
|-----------|--------|
| `/api/stores/` (118 do'kon) | **barchasida `logo: null`** |
| `/api/stores/110/` mahsulotlari | **barchasida `cover: null`, `images: []`** |
| `/api/ads/` (33 e'lon) | **barchasida `cover: null`** |
| `/api/seed-status/` | `seeded: true` — 99 user, 708 mahsulot (hammasi seed) |

**Muhim dalil:** DB'da birorta ham media FAYL HAVOLASI yo'q. Agar fayllar
"yuklangandan keyin yo'qolganida" (ephemeral disk stsenariysi) — DB'da yo'l
qolar, rasm 404 bo'lardi. Bizda esa maydonlar bo'sh → yuklash tranzaksiyasi
umuman yakunlanmagan (PutObject xatosi hammasini qaytargan). Bu 1-bo'limdagi
ACL diagnozini tasdiqlaydi.

## 4. Render environment o'zgaruvchilari

`render.yaml` (blueprint) bo'yicha:

| O'zgaruvchi | Qiymat | Holat |
|-------------|--------|-------|
| `AWS_STORAGE_BUCKET_NAME` | `media` | Blueprint'da bor |
| `AWS_S3_ENDPOINT_URL` | `https://shyllblzdbjctcbwgzun.storage.supabase.co/storage/v1/s3` | Blueprint'da bor |
| `AWS_S3_REGION_NAME` | `ap-northeast-1` | Blueprint'da bor |
| `AWS_ACCESS_KEY_ID` | `sync: false` | ⚠️ **Panelda qo'lda kiritilgan bo'lishi SHART — tashqaridan tekshirib bo'lmaydi** |
| `AWS_SECRET_ACCESS_KEY` | `sync: false` | ⚠️ Yuqoridagi kabi |

**Tekshirish yo'li (siz uchun):** Render → samcity → Environment'da ikkala
kalit borligini ko'ring. Yoki yangi deploy'dan keyin loglarning BOSHIDA
`[media] OGOHLANTIRISH: ... AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY BO'SH`
satri bor-yo'qligiga qarang — bu ogohlantirish aynan shu holat uchun qo'shilgan.
(Satr BO'LSA — kalitlar kiritilmagan; BO'LMASA — kalitlar joyida.)

## 5. Render loglari (yuklash payti) — nimani qidirish kerak

Dashboard'ga kirish imkonim yo'q, shuning uchun aniq belgilar ro'yxati:

- **Eski kod (hozirgi running)**: yuklashda `S3UploadFailedError` /
  `ClientError ... PutObject ... InvalidRequest/AccessDenied` (x-amz-acl tufayli)
  + so'rov `500` bilan tugaydi.
- **Kalitlar bo'sh bo'lsa (yangi kodda)**: startup'da `[media] OGOHLANTIRISH ...`.
- **Hammasi to'g'ri bo'lsa**: yuklash `200/302`, log'da S3 xatosi yo'q.

## 6. Brauzer Network probe'lari (bajarilgani)

- Rasm GET: prod sahifalarida `<img>` teg umuman chiqmayapti (media yo'q,
  hamma joyda placeholder) — 3-bo'limdagi holatga mos.
- Supabase GET probe'lari — 2-bo'limdagi jadval.
- **Upload POST testi bajarilmadi**: demo do'konga test-logo yuklash production
  yozuvi bo'lgani uchun ruxsat tizimi to'xtatdi (audit read-only). Deploy
  yangilangach 8-bo'limdagi rejaga qarang.

## 7. To'rt gipoteza bo'yicha hukm

| Gipoteza | Hukm | Dalil |
|----------|------|-------|
| Fayl umuman saqlanmayapti | ✅ **TASDIQLANDI (root cause)** | Eski koddagi `public-read` ACL + DB'da birorta havola yo'q + bucket bo'sh |
| Saqlangan, lekin URL buzuq | ❌ | Bucket'da obyekt yo'q; URL sxemasi jonli tekshiruvda to'g'ri |
| Render lokal diskiga saqlangan (ephemeral) | ❌ | Bo'lsa DB'da `/media/...` yo'llar qolardi — yo'llar yo'q |
| Supabase'ga saqlangan, lekin ochilmayapti | ❌ | Bucket mavjud-u bo'm-bo'sh |

**Qo'shimcha (ikkinchi darajali) sabab:** `main` branch 6 commit orqada
qolgan edi (`d2e7efc` ← media tuzatishi `9828879` dan OLDINGI holat).
Ya'ni tuzatish 2026-07-12'da yozilgan, lekin deploy branchiga yetmagan.
Bugun (2026-07-13) `master:main` push qilindi — **lekin audit paytida prod
hali eski kodda** (`/api/catalog/` → 404, yangi serializer maydonlari yo'q).
Deploy tugaganini tekshirish kerak (autoDeploy yoqilgan; build cho'zilishi
yoki xato bo'lishi mumkin — Render dashboard'da Events'ga qarang).

## 8. Keyingi qadamlar (kod o'zgarishi KERAK EMAS — hammasi repo'da tayyor)

1. **Deploy'ni tasdiqlang**: Render → samcity → Events. Yangi build o'tgach
   `GET /api/catalog/` 200 qaytarishi kerak (hozir 404 = eski kod).
2. **Kalitlarni tekshiring**: Environment'da `AWS_ACCESS_KEY_ID` /
   `AWS_SECRET_ACCESS_KEY` (Supabase → Project Settings → Storage → S3 access
   keys). Startup logida `[media] OGOHLANTIRISH` chiqmasligi kerak.
3. **Supabase bucket "Public" ekanini tasdiqlang**: Supabase dashboard →
   Storage → `media` → Public bucket ✓ (ACL endi ishlatilmaydi — ochiq kirish
   faqat shu sozlamadan keladi).
4. **Diagnostika buyrug'i** (yangi kodda bor): Render Shell (yoki lokalda prod
   env bilan) `python manage.py check_media` — yozish/o'qish/URL'ni bosqichma-
   bosqich tekshiradi.
5. **Jonli test**: saytga kirib istalgan do'konga logo/mahsulot rasmi yuklang →
   rasm `https://shyllblzdbjctcbwgzun.storage.supabase.co/storage/v1/object/public/media/...`
   URL bilan chiqishi va redeploy'dan keyin ham qolishi kerak.
6. Eski buzuq havolalarni tozalash SHART EMAS — DB'da buzuq havola yo'q
   (hech narsa saqlanmagani uchun).

---
*Audit davomida productionga hech narsa yozilmadi. Foydalanilgan probe'lar:
ochiq sahifalar, ochiq API (o'qish), Supabase public endpoint xato-javoblari,
git tarixi (`d2e7efc` vs `9828879` diff).*
