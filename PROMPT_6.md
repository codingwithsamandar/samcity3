# Claude Code uchun topshiriq — 1-to'lqin (1-qism): ovozli oqim + UI kartalar

0-to'lqin tugadi (270 test, injection yopilgan). Endi 1-to'lqin — **ovoz**.
Butun to'lqin katta, shuning uchun bu **birinchi bo'lak**: kalitga bog'liq
bo'lmagan, o'zi ishlaydigan **gapiradigan demo**.

Maqsad: foydalanuvchi web widget'da mikrofon bosib gapiradi → agent javob
beradi → kartalar ekranga chiqadi → javob ovozda yangraydi. Aynan
`JARVIS_REJA.md` 0-bo'limidagi lavash ssenariysining web versiyasi.

Kontekst: `JARVIS_REJA.md` (0, 3.7, 3.8-bo'limlar), `JARVIS_TEXNIKALAR.md`
(T1, T11, T13, T14), `assistant/templates/assistant/_widget.html` (mavjud widget).

---

## ⚠️ Nima bu bo'lakda YO'Q (keyingi bo'laklar)

- **Mohir.ai STT** — kalit yo'q. Hozircha brauzer Web Speech (`uz-UZ`)
  ishlatiladi. STT'ni **interfeys ortiga** qo'y (`stt.py`) — Mohir keyin
  ulanadi, widget o'zgarmaydi.
- **Flutter ovozli rejimi** — keyingi bo'lak. Faqat web.
- **Barge-in** (gapni bo'lish) — 3-bo'limda alohida, lekin protokolni
  hozir buzma.

Bu bo'lak **yangi API kalit talab qilmaydi** — Aisha TTS allaqachon
sozlangan (`tts.py`), brauzer STT bepul.

---

## 1. UI direktivalarini widget'da chizish

Agent allaqachon `ui` qaytaradi (`card_list`, `product_grid`,
`confirm_payment`...). Hozir widget faqat joy kartalarini biladi. Uni
umumiy UI-render qiladigan qil.

`_widget.html` (yoki alohida `_widget.js`) da `renderUI(ui)` funksiyasi:

| `ui.type` | Chiziladi |
|---|---|
| `card_list` | do'kon/joy ro'yxati — sarlavha, subtitle, tugma |
| `product_grid` | rasm + narx + «tanlash» tugmasi |
| `confirm_payment` | summa taqsimoti + **Tasdiqlash** / **Bekor** tugmalari |
| `text` | oddiy matn (fallback) |

Shartlar:
- Har kartada `id` bo'lsin (`store:12`) — bosilganda `sendMessage` ga
  o'sha element haqida xabar yuborsin (masalan «Anor Fast Food ni tanladim»)
- `confirm_payment` tugmasi `/ai/confirm/<pending_id>/` ga POST yuborsin
  (CSRF bilan — widget'da allaqachon `samAiCsrf` bor)
- **Bekor** → `/ai/cancel/<pending_id>/`
- Tashqi kutubxonasiz (vanilla JS — mavjud uslub), sayt CSS
  o'zgaruvchilaridan foydalansin (light/dark)

---

## 2. «Kartalar oldin, ovoz keyin» — kechikish hiylasi

`JARVIS_REJA.md` 0-bo'lim: kartalar tool natijasi kelishi bilan **darhol**
chiziladi, ovoz keyin. Odam ko'zi bilan ko'rgani uchun kutish sezilmaydi.

Oqim:

```
1. javob keldi (reply + ui + pending_id)
2. renderUI(ui)          ← DARHOL, ovozdan oldin
3. matnni ekranga yoz
4. speakStreaming(reply) ← keyin
```

---

## 3. Oqimli TTS (T11 — sintez va ijro parallel)

Hozir TTS butun matnni bitta so'rovda oladi — uzun javobda sekin. Buni
jumla-jumla qil:

1. `reply` ni jumlalarga ajrat (o'zbekcha: `35 000`, `soat 14.30`, `va h.k.`
   bo'linmasin — `llm.py` da bu mantiq bor, qayta ishlat yoki umumiy modulga
   chiqar)
2. Har jumla uchun `/ai/tts/` dan audio ol
3. **Producer/consumer**: 2-jumla 1-jumla yangrayotganda tayyorlanadi
   (JS'da: `Audio` navbati, `onended` da keyingisini boshla)
4. Birinchi jumla audiosi kelishi bilan yangrasin — qolganini kutmasin

Server tomon (`assistant/tts.py`) allaqachon bitta matn oladi — o'zgartirma,
faqat widget qisqa jumlalar yuborsin.

---

## 4. Ovozli rejim holatlari

Widget'da aniq ko'rinadigan holatlar (mavjud animatsiyani kengaytir):

- `IDLE` — tayyor
- `LISTENING` — mikrofon ochiq, to'lqin animatsiyasi
- `THINKING` — agent javob kutilmoqda, «...» yoki spinner
- `SPEAKING` — javob yangramoqda

Web Speech `uz-UZ` bilan sozlansin. Interim (partial) natija ekranda jonli
ko'rinsin (T9 — kutish sezilmaydi).

---

## 5. STT interfeysi (kelajak uchun)

`assistant/stt.py` yarat — hozircha faqat interfeys + brauzer izohi:

```python
def transcribe(audio_bytes, lang='uz'):
    """Ovoz→matn. Hozircha None (brauzer Web Speech ishlatadi).

    Mohir.ai ulangach shu funksiya audio olib matn qaytaradi.
    Widget avval /ai/stt/ ga urinadi, 204 kelsa brauzer Web Speech'ga qaytadi
    (tts.py dagi bir xil «muloyim degradatsiya» naqshi).
    """
    return None
```

`/ai/stt/` endpoint qo'sh (web + `/api/assistant/stt/`): audio olsa
`transcribe()` chaqiradi, `None` bo'lsa **204** qaytaradi. Widget 204 ni
ko'rib brauzer STT'ga qaytadi. Bu Mohir'ni keyin **widget'ga tegmasdan**
ulash imkonini beradi.

---

## 6. Kechikish o'lchovi

Widget konsoliga (yoki `AgentAuditLog` ga) yozib bor:
- STT tugadi → javob keldi: necha ms
- javob keldi → birinchi audio yangradi: necha ms

`JARVIS_REJA.md` maqsadi: **2.5 soniyadan kam**. Hozirgi holatni o'lcha va
hisobotga yoz (Groq sekin bo'lgani uchun bu bo'lakda maqsadga yetmasligi
mumkin — muhimi o'lchash).

---

## Bajarish tartibi

1. UI render (1) + kartalar bosilishi
2. Kartalar-oldin oqimi (2)
3. Oqimli TTS (3)
4. Holatlar + Web Speech uz-UZ (4)
5. STT interfeysi + /ai/stt/ endpoint (5)
6. Kechikish o'lchovi (6)
7. Server qismlariga test (`/ai/stt/` 204, confirm/cancel widget'dan)
8. `python manage.py test assistant` — o'tsin (hozir 270)

## Test cheklovi

Widget asosan JS/HTML — unit-test qiyin. Shuning uchun:
- **Server** qismlarini test qil (`/ai/stt/` 204, endpoint'lar)
- **Widget**ni qo'lda tekshir: `python manage.py runserver`, brauzerda och,
  smoke foydalanuvchi bilan kir (998900000777), «lavash» deb yoz/gapir,
  kartalar chiqishini, tanlash, tasdiq oqimini ko'r
- Qo'lda tekshirish natijasini hisobotga yoz (skrinshot shart emas, matn
  tavsifi yetarli)

## Hisobotda kerak

1. Widget'da lavash ssenariysi qay darajada ishlaydi (qadam-qadam)
2. Kechikish: STT→javob, javob→ovoz (ms)
3. Kartalar-oldin sezilarli farq berdimi
4. Oqimli TTS ishladimi (birinchi jumla tez yangradimi)
5. Web Speech uz-UZ sifati (o'zbekchani qanday taniydi)
6. Nima ishlamadi yoki g'aliz

## Chegara

- Mohir STT ulanmaydi (kalit yo'q) — faqat interfeys
- Flutter'ga tegilmaydi
- Barge-in bu bo'lakda yo'q, lekin TTS to'xtatish funksiyasi (`stop()`)
  bo'lsin — keyin barge-in shunga ulanadi
- Arxitektura o'zgarishi bo'lsa — hisobotda ayt, o'zing qilma

`git commit` qilma. Ortiqcha maqtov kerak emas — nima ishlamadi, shuni ayt.
