# To'lov shlyuzi — Payme + Click (sozlash qo'llanmasi)

Universal to'lov integratsiyasi: **Payme** (Merchant API / JSON-RPC) va **Click**
(Shop API / Prepare-Complete). To'rtta tur uchun ishlaydi — **delivery buyurtma,
taksi, booking, xizmat to'lovlari**.

## 1. Avval — migratsiya va test

```bash
python manage.py migrate payments      # yangi Transaction jadvali
python manage.py test payments         # Payme + Click oqimlari testlari
```

## 2. Arxitektura
- `payments/models.py` → **Transaction** (universal: provider, target_type,
  target_id, amount, state). Payme state semantikasi: 1=yaratildi, 2=to'landi,
  -1/-2=bekor.
- `payments/gateways.py` → **registry**: har tur uchun (topish, egasi, summa,
  to'langanmi, to'landi/bekor belgilash). Yangi tur qo'shish = shu yerga 1 ta yozuv.
- `payments/payme.py` → Payme JSON-RPC view + checkout URL generatori.
- `payments/click.py` → Click Prepare/Complete view'lari + URL generatori.
- `api/payment_views.py` → mobil ilova uchun `POST /api/payments/initiate/`.

## 3. Webhook URL'lari (provayder kabinetida ko'rsatiladi)
| Provayder | URL |
|-----------|-----|
| Payme     | `https://<domen>/payments/payme/` |
| Click Prepare  | `https://<domen>/payments/click/prepare/` |
| Click Complete | `https://<domen>/payments/click/complete/` |

## 4. Sozlamalar (env o'zgaruvchilari)
```bash
# Payme
PAYME_MERCHANT_ID=...        # kabinetdan
PAYME_MERCHANT_KEY=...        # webhook auth kaliti (MAXFIY)
# Click
CLICK_SERVICE_ID=...
CLICK_MERCHANT_ID=...
CLICK_SECRET_KEY=...          # imzo (sign) kaliti (MAXFIY)
CLICK_MERCHANT_USER_ID=...
```
Kalitlar bo'sh bo'lsa — webhook'lar autentifikatsiyadan o'tmaydi (xavfsiz default).

## 5. Mobil/web qanday foydalanadi
1. Mijoz buyurtma/sayohat/bron yaratadi (hozirgidek, `payment_status=unpaid`).
2. Ilova `POST /api/payments/initiate/` ga `{target_type, target_id}` yuboradi
   (target_type: `order` | `trip` | `booking` | `service`).
3. Javob: `{amount, payme_url, click_url}`. Ilova kerakli URL'ni ochadi.
4. Foydalanuvchi to'laydi → provayder webhook'ni chaqiradi → tizim obyektni
   avtomatik **paid** (booking uchun **confirmed**) qiladi.

Xavfsizlik: foydalanuvchi faqat **o'ziga tegishli** obyekt uchun to'lov boshlay
oladi (egalik tekshiruvi). Webhook'lar imzo/auth bilan himoyalangan, summa
solishtiriladi, ikki marta to'lash bloklanadi.

## 6. Muhim eslatma
- Karta ma'lumotlari (raqam/CVV) **saqlanmaydi** — to'lov provayder sahifasida.
- Eski "demo" karta oqimi (checkout'da `paid` belgilash) hali ham bor; real
  to'lovga o'tish uchun ilovani `initiate` + provayder URL oqimiga ulang.
- Test rejimida provayderlarning sandbox kalitlaridan foydalaning.
