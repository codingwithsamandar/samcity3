# 1-to'lqin, 1-qism — ovozli oqim + UI kartalar (hisobot)

Bo'lak: web widget gapiradigan demo. Yangi kalit talab qilinmaydi (Aisha TTS
avvaldan, brauzer STT bepul). Mohir STT — faqat interfeys.

## Qamrov

| Fayl | O'zgarish |
|---|---|
| `assistant/stt.py` | YANGI — `transcribe()` interfeysi (hozircha None → 204) |
| `assistant/views.py` | `/ai/stt/` endpoint + `X-STT-Available` sarlavhasi |
| `assistant/urls.py` | `stt/` yo'li |
| `api/assistant_views.py` | `AssistantSTTView` + `RawMediaParser` (audio/webm 415'ni tuzatadi) |
| `api/urls.py` | `assistant/stt/` |
| `assistant/templates/assistant/_widget.html` | renderUI, kartalar-oldin, oqimli TTS, holatlar, mic 2-yo'li |
| `assistant/tests/test_stt.py` | YANGI — 10 test |

**280 test o'tadi** (270 → 280). `python manage.py check` toza, migratsiya drifti yo'q.

---

## 1. Lavash ssenariysi — qadam-qadam (brauzerda tekshirilgan)

Dev server (`runserver 8023`), widget brauzerda ochildi. Konsolda JS xatosi
**yo'q**. Har bir UI turi va oqim DOM darajasida tekshirildi:

| Qadam | Natija |
|---|---|
| Widget yuklanishi | ✅ IIFE ishga tushdi, holat=IDLE, xatosiz |
| `card_list` render | ✅ 2 ta tanlanadigan karta (sarlavha, subtitle, → o'q) |
| Karta bosish | ✅ «Anor Fast Food ni tanladim» yubordi (nom bo'yicha tanlash) |
| `product_grid` render | ✅ 3 mahsulot, narx «35 000 so'm» formatida, «➕ Savatga» tugma |
| «Savatga» bosish | ✅ «Lavash (katta) ni savatga qo'sh» yubordi |
| `confirm_payment` render | ✅ ajratmalar + jami 80 000 + izoh + Tasdiqlash/Bekor |
| **Tasdiqlash** bosish | ✅ `/ai/confirm/<id>/` ga POST → karta `done`, tugma o'chdi, «Buyurtma qabul qilindi ✅» |
| Engine kartalari (real) | ✅ «eng yaqin dorixona» real `/ai/chat/` orqali 6 joy kartasi — eski render buzilmagan |

**Muhim eslatma (halol baho):** UI render sinovlari `window.fetch` ni
vaqtincha soxta **agent javobiga** almashtirib bajarildi — Groq **kunlik
kvotasi** (200k/kun) oldingi bosqichlarda deyarli tugagani uchun jonli LLM bilan
uchdan-uchgacha yugurtirmadim (kvota tejash). Lekin:

- Soxta javoblar `ui.py`/`tools/delivery.py` chiqaradigan struktura bilan
  **bayt-ma-bayt bir xil** (aynan o'sha maydonlar).
- Agent bu strukturalarni haqiqatda chiqarishi PROMPT_3–5 smoke-testlarida
  allaqachon tasdiqlangan (`find_store→card_list`, `cart_add`,
  `propose_order→confirm_payment` — audit jurnalida).
- Engine kartalari esa jonli, real endpoint bilan tekshirildi.

Ya'ni ikki uch — «agent to'g'ri UI chiqaradi» (avval) va «widget UI'ni to'g'ri
chizadi» (hozir) — birga lavash ssenariysini qamraydi. Jonli login+agent+kvota
sinovi qoldirildi; ishga tushirish: smoke user (998900000777) bilan kirib
«lavash bor do'konlarni ko'rsat».

---

## 2. Kechikish (ms)

Widget konsoliga yoziladi (`console.log('[SamAI] ...')`):
- `so'rov→javob` — mock javobda 1-2 ms (haqiqiy Groq'da PROMPT_5 o'lchoviga
  ko'ra ~1500-3000 ms).
- `javob→birinchi audio` — server TTS'da birinchi jumla kelgunga qadar.

⚠️ **JARVIS_REJA maqsadi 2.5s** — bu bo'lakda o'lchash uchun jonli Groq kerak,
kvota tugagani sabab to'liq raqam olinmadi. Mexanizm (o'lchov nuqtalari)
o'rnatildi; kvota tiklangач aniq raqam olinadi. Groq'ning sekinligi (reasoning
model) 2.5s'ga yetishni qiyinlashtiradi — bu model tanlash masalasi (PROMPT_5
hisobotida qayd etilgan).

---

## 3. Kartalar-oldin — sezilarli farqmi

Kod darajasida: `send()` javob kelgach butun VIZUAL qismni (matn + `renderUI` +
kartalar) **sinxron** chizadi, ovoz (`speakStreaming`) eng oxirida. Ya'ni
foydalanuvchi kartalarni ovoz tayyorlanishidan oldin ko'radi. Mock javobda
kartalar darhol (1-2ms) chiqdi. Haqiqiy TTS kechikishi (~0.5-1s) shu paytda
yashiringan bo'ladi — real audio bilan farq seziladi (bu bo'lakda o'lchanmadi).

---

## 4. Oqimli TTS

- **Jumla ajratgich** brauzerda tekshirildi — barcha o'zbekcha tuzoqlar to'g'ri:
  «Salom. Qandaysiz?»→2; «35 000 so'm»→1; «8.5 km»→1; «soat 14.30»→1;
  «va h.k.»→1; «Zo'r! Nima olasiz?»→2. (Python `llm.split_sentences` bilan aynan
  mirror, u avvaldan test qilingan.)
- **Producer/consumer**: `speakStreaming` 1-jumla audiosini kutmasdan
  yangratadi, 2-jumlani shu payt tayyorlaydi (`ensure(i+1)`), `onended` da
  keyingisiga o'tadi. `speakSeq` bilan yangi javob eskisini bekor qiladi
  (barge-in poydevori).
- Jonli TTS audio ijrosini brauzer preview'da to'liq eshitib bo'lmadi (audio
  qurilma yo'q) — lekin oqim mantiqi va jumla chegaralari tasdiqlangan.

---

## 5. Web Speech uz-UZ

- Til `uz-UZ`, `interimResults=true` — jonli (partial) natija `input` ga yoziladi
  (kutish sezilmaydi, T9). `language-not-supported` bo'lsa `ru-RU` ga tushadi.
- ⚠️ O'zbekchani qay darajada taniydi — **brauzerga bog'liq** va bu muhitda
  (audio qurilmasiz preview) sinab bo'lmadi. Chrome `uz-UZ` ni qo'llaydi, lekin
  aniqlik past bo'lishi mumkin — shuning uchun Mohir STT rejalashtirilган.
  Mohir ulanганда widget o'zgarmasdan server STT'ga o'tadi (`X-STT-Available`).

---

## 6. Holatlar

`IDLE / LISTENING / THINKING / SPEAKING` — `data-state` atributi + header matni +
nuqta rangi. Brauzerda tsikl tasdiqlandi: **IDLE → THINKING → SPEAKING**
(MutationObserver bilan). LISTENING mic bosilganda. TTS/utterance tugaganda IDLE.

---

## 7. STT interfeysi

- `/ai/stt/` (web) va `/api/assistant/stt/` (mobil) — audio olsa `transcribe()`
  chaqiradi, None bo'lsa **204 + `X-STT-Available: 0`**. Brauzerda tasdiqlandi:
  204, sarlavha `0`.
- Widget init'da probe qiladi; `0` → brauzer Web Speech (hozirgi holat).
  Mohir kalit qo'yilsa `is_enabled()`→True → sarlavha `1` → widget **o'zgarmasdan**
  MediaRecorder→/ai/stt/ yo'liga o'tadi.
- DRF `audio/webm` ni 415 bilan rad etardi — `RawMediaParser` tuzatdi.

---

## Nima ishlamadi / g'aliz

1. **Screenshot tool takror timeout berdi** (renderer band) — DOM tekshiruvi
   bilan aylanib o'tdim (u kuchliroq dalil). Vizual skrinshot yo'q.
2. **Jonli Groq LLM va TTS audio** — kvota + preview audio qurilmasi yo'qligi
   sabab uchdan-uchgacha eshitib/o'lchab bo'lmadi. Struktura va mantiq
   tekshirildi; jonli raqamlar kvota tiklangач olinadi.
3. `--noreload` sabab widget o'zgarganda serverni qayta ishga tushirish kerak
   bo'ladi (preview-server odati).

## Arxitektura eslatmasi (o'zim qilmadim)

- **Barge-in** bu bo'lakda yo'q (rejaga ko'ra), lekin `stop()` funksiyasi tayyor
  va mic bosilganda chaqiriladi — keyingi bo'lak shunga ulanadi.
- Kelgusi model tanlash: reasoning model (gpt-oss) TTS+2.5s maqsadga xalaqit
  beradi — PROMPT_5 hisobotidagi tavsiya kuchda qoladi.
