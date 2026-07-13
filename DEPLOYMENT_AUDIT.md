# SamCity — Production Deployment Audit (media storage)

> Sana: 2026-07-13 · Usul: kod tahlili + jonli production probe'lari
> (samcity.onrender.com API + Supabase storage endpoint, faqat GET/HEAD).
> **Kod o'zgartirilmagan. Productionga hech narsa yozilmagan.**
>
> Oldingi hisobot: [MEDIA_AUDIT_REPORT.md](MEDIA_AUDIT_REPORT.md) (kecha, eski kod
> ishlab turganda). Bugungi audit YANGI deploy'dan keyingi holatni aks ettiradi —
> vaziyat o'zgargan, quyida yangilangan diagnoz.

---

## 0. To'rt savolga qisqa javob

| Savol | Javob |
|-------|-------|
| **1. Yuklangan fayllar aslida qayerda?** | **Supabase S3, `media` bucket ichida.** Jonli tasdiqlandi: yangi yuklangan logo public URL orqali 200 qaytaradi (9 423 bayt, image/jpeg). |
| **2. Nega fayllar "yo'qolyapti"?** | Endi yo'qolmayapti — **fayl saqlanadi, lekin Django yasayotgan URL noto'g'ri** (`/storage/v1/s3/...` — S3 API endpoint, u GET'da 403 beradi). Rasm brauzerda chiqmagani uchun "yo'qolgan"dek ko'rinadi. |
| **3. Supabase storage faolmi?** | **HA.** Yozish ishlaydi, fayl redeploy'dan keyin ham turibdi, bucket public. |
| **4. Django hali ham lokal `media/` ga yozyaptimi?** | **YO'Q (production'da).** `STORAGES['default']` = `S3Boto3Storage` (env'da `AWS_STORAGE_BUCKET_NAME=media` bor). Lokal dev'da esa ha — `.env` da S3 kalitlari yo'q, `FileSystemStorage` ishlaydi (bu to'g'ri xatti-harakat). |

---

## 1. Hozirgi holat — nima o'zgardi (kechagi auditga nisbatan)

Kechagi diagnoz: eski kod (`d2e7efc`, `AWS_DEFAULT_ACL='public-read'`) tufayli
upload umuman ishlamasdi. Bugun:

1. `master:main` push qilingan (`29c0948`) — **Render yangi kodni deploy qilgan.**
   Dalil: `GET /api/catalog/` endi **401** qaytaradi (kecha 404 edi = route
   umuman yo'q edi; 401 = route bor, faqat login talab qiladi — bu
   `CatalogListView` uchun atayin qilingan, [api/delivery_views.py:81](api/delivery_views.py:81)).
2. **Upload endi ishlayapti.** Do'kon id=125 («do'konchi») ga logo yuklangan va
   u Supabase'da haqiqatan mavjud (2-bo'lim dalillari).
3. **Yangi (qolgan yagona) muammo:** API qaytarayotgan URL:

   ```
   https://shyllblzdbjctcbwgzun.storage.supabase.co/storage/v1/s3/media/delivery/stores/yz.jpg   ← 403
   ```

   To'g'ri public URL esa:

   ```
   https://shyllblzdbjctcbwgzun.storage.supabase.co/storage/v1/object/public/media/delivery/stores/yz.jpg   ← 200 ✅
   ```

## 2. Jonli probe natijalari (2026-07-13)

| So'rov | Natija | Ma'nosi |
|--------|--------|---------|
| `GET /api/health/` | 200 `{"status":"ok"}` | Servis tirik |
| `GET /api/catalog/` | 401 (kecha: 404) | **Yangi kod deploy bo'lgan** |
| `GET /api/stores/` | id=125 `logo: ...storage/v1/s3/media/delivery/stores/yz.jpg` | Upload muvaffaqiyatli, DB'da yo'l bor |
| `HEAD .../object/public/media/delivery/stores/yz.jpg` | **200**, image/jpeg, 9423 B | **Fayl Supabase'da BOR, bucket public** |
| `HEAD .../storage/v1/s3/media/delivery/stores/yz.jpg` | **403** | Django yasagan URL S3 API'ga ishora qiladi — imzosiz GET taqiqlangan |
| Qolgan 117 do'kon | `logo: null` | Eski davrda (buzuq ACL kodi) hech narsa saqlanmagan — tozalash kerak emas |

## 3. Root cause — nega URL noto'g'ri

[sdev/settings.py:296-306](sdev/settings.py:296) da Supabase uchun to'g'ri
`MEDIA_URL` (`.../object/public/media/`) hisoblanadi, **lekin bu o'lik kod**:

- `ImageField.url` → `S3Boto3Storage.url()` ni chaqiradi, u **`MEDIA_URL` ni
  umuman ishlatmaydi**. django-storages URL'ni shunday quradi:
  - `AWS_S3_CUSTOM_DOMAIN` bo'lsa → `https://<custom_domain>/<key>`;
  - bo'lmasa → `<AWS_S3_ENDPOINT_URL>/<bucket>/<key>` (path-style, imzosiz,
    chunki `AWS_QUERYSTRING_AUTH=False`).
- Bizda `AWS_S3_CUSTOM_DOMAIN` bo'sh ([render.yaml](render.yaml) da umuman yo'q),
  shuning uchun URL endpoint'dan yasaladi:
  `https://.../storage/v1/s3` + `/media/` + `<key>` → aynan API'dan kelayotgan
  buzuq havola.
- Supabase'ning `/storage/v1/s3/...` yo'li faqat imzolangan S3 so'rovlar uchun;
  brauzerdan oddiy GET → 403. Public o'qish faqat
  `/storage/v1/object/public/<bucket>/...` orqali.

`entrypoint.sh` har deploy'da ishga tushiradigan `check_media` buyrug'i buni
allaqachon ko'rsatayotgan bo'lishi kerak: 1–4-qadamlar (yoz/o'qi) `[OK]`,
5-qadam (Public HTTP GET) esa `[XATO] public URL faylni qaytarmadi...`
([main/management/commands/check_media.py:88-102](main/management/commands/check_media.py:88)).
Render loglarida shuni ko'rasiz — bu diagnozning yana bir tasdig'i.

## 4. Render environment tekshiruvi

[render.yaml](render.yaml:96-106) bo'yicha:

| O'zgaruvchi | Qiymat | Holat |
|-------------|--------|-------|
| `AWS_STORAGE_BUCKET_NAME` | `media` | ✅ To'g'ri (bucket jonli tasdiqlangan) |
| `AWS_S3_ENDPOINT_URL` | `https://shyllblzdbjctcbwgzun.storage.supabase.co/storage/v1/s3` | ✅ Yozish ishlayapti |
| `AWS_S3_REGION_NAME` | `ap-northeast-1` | ✅ (imzo xatosi yo'q) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | panelda (`sync: false`) | ✅ **Kiritilgan** — aks holda upload umuman o'tmasdi; logo saqlangani buni isbotlaydi |
| `AWS_S3_CUSTOM_DOMAIN` | **YO'Q** | ❌ **Yagona kamchilik — URL muammosining sababi** |

## 5. Django lokal `media/` ga yozyaptimi?

- **Production:** yo'q. `AWS_STORAGE_BUCKET_NAME` o'rnatilgani uchun
  [sdev/settings.py:262-294](sdev/settings.py:262) `STORAGES['default']` ni
  `S3Boto3Storage` ga almashtiradi. Jonli dalil: yuklangan fayl Supabase'da
  paydo bo'ldi. `sdev/urls.py:22-23` dagi lokal `/media/` serving faqat
  `DEBUG=True` da ulanadi (prod'da `DJANGO_DEBUG=False`).
- **DB'da lokal yo'l qoldiqlari yo'q:** birorta yozuvda
  `https://samcity.onrender.com/media/...` ko'rinishidagi havola uchramadi —
  demak ephemeral diskka yozilib yo'qolgan fayl stsenariysi ham yo'q.
- **Lokal dev:** `.env` da S3 kalitlari yo'q → `FileSystemStorage` +
  `BASE_DIR/media` — bu atayin shunday va to'g'ri.
- Eslatma: `logs/` katalogi konteyner ichida yoziladi (RotatingFileHandler) —
  bu media emas, redeploy'da yo'qolishi normal.

## 6. Tuzatish rejasi (KOD O'ZGARISHI KERAK EMAS — bitta env qiymati)

Render → `samcity` → Environment ga qo'shing:

```
AWS_S3_CUSTOM_DOMAIN = shyllblzdbjctcbwgzun.storage.supabase.co/storage/v1/object/public/media
```

(protokolsiz, oxirida `/` siz — django-storages o'zi `https://<qiymat>/<key>`
qilib quradi; [sdev/settings.py:297-298](sdev/settings.py:297) dagi `MEDIA_URL`
ham avtomatik shu bilan moslashadi.)

Saqlagach Render avtomatik redeploy qiladi. Keyin tekshiruv:

1. Render loglarida `check_media` 5-qadami endi `[OK] fayl public URL orqali
   o'qildi` bo'lishi kerak.
2. `GET /api/stores/` → id=125 logo `.../object/public/media/...` bilan chiqadi
   va brauzerda ochiladi.
3. **DB'ni tuzatish kerak emas** — bazada faqat nisbiy yo'l saqlanadi
   (`delivery/stores/yz.jpg`), buzuq URL har so'rovda dinamik yasalgan edi.
   Custom domain o'rnatilishi bilan mavjud yozuv ham to'g'ri URL bilan chiqadi.
4. Eski davr fayllarini tiklash shart emas — buzuq ACL davrida hech narsa
   saqlanmagan (117 do'konda `logo: null`), yo'qotilgan fayl yo'q.

## 7. Gipotezalar bo'yicha yakuniy hukm

| Gipoteza | Hukm | Dalil |
|----------|------|-------|
| Fayl umuman saqlanmayapti | ❌ (kecha ha edi, bugun yo'q) | id=125 logo Supabase'da 200 |
| **Saqlangan, lekin URL buzuq** | ✅ **HOZIRGI ROOT CAUSE** | `/storage/v1/s3/...` → 403; `/object/public/...` → 200 |
| Render lokal diskiga yozilgan (ephemeral) | ❌ | DB'da lokal yo'l yo'q; storage backend S3 |
| Supabase o'chiq/kalit yo'q | ❌ | Yozish muvaffaqiyatli — kalitlar panelda kiritilgan |

---
*Foydalanilgan probe'lar: `/api/health/`, `/api/catalog/`, `/api/stores/`
(ochiq, faqat o'qish), Supabase public/S3 endpoint'lariga HEAD so'rovlar.
Hech qanday yozuv/o'zgartirish qilinmagan.*
