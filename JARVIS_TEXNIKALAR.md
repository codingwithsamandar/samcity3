# Mark XLIX — texnik ekstrakt

> Mark XLIX (FatihMakes) loyihasining **to'liq tahlili**: `main.py` (1350 qator),
> `core/` (llm_client, stt, tts, prompt), `memory/`, `actions/` (19 fayl), `dashboard/`.
>
> ⚠️ **Litsenziya: CC BY-NC 4.0 — tijorat uchun kod ko'chirish MUMKIN EMAS.**
> Bu hujjat kod emas, **texnika va bilim** to'plami. G'oyalar mualliflik huquqi
> bilan himoyalanmaydi. Barcha kod SamCity arxitekturasi uchun **noldan yoziladi**
> (u baribir mos emas edi — desktop → server).

---

## Qisqacha xulosa

| Kategoriya | Topildi | Qiymati |
|---|---|---|
| ✅ **Olinadigan texnika** | **31 ta** | Rejaga qo'shildi |
| ⚠️ Moslashtirish kerak | 8 ta | Desktop → server |
| ❌ Yaroqsiz | `actions/` (19 fayl) | 0% mos |

**Eng qimmatli 5 tasi:** oqimli TTS jumla ajratish · tool-call fragment yig'ish ·
gapni bo'lish (barge-in) · vaqt konteksti in'ektsiyasi · tegli tizim xabarlari.

---

## 1. LLM qatlami (`core/llm_client.py`)

### T1. Jumla chegarasi bo'yicha oqim → TTS *(eng muhim)*

LLM oqimidan gaplar **tugashini kutmasdan** ajratiladi va darrov TTS ga yuboriladi.
Kechikishni ~1.5 s kamaytiradi.

Naqsh: `(?<=[.!?])\s+` yoki bo'sh qator. Nuqta atrofida **probel talab qilinadi** —
shuning uchun `3.5` kabi o'nlik son bo'linib ketmaydi.

⚠️ **O'zbek tili uchun moslashtirish shart** — ular hisobga olmagan:

```
"35 000 so'm"     → probelli son, jumla emas
"8.5 km"          → o'nlik
"soat 14.30"      → vaqt
"t.me/..."        → havola
"va h.k."         → qisqartma
"1-chi", "2-chi"  → tartib son
```

Bizning versiyamiz bu holatlar uchun oldindan tekshiruv qo'shadi.

### T2. Oqimli tool-call fragmentlarini yig'ish

**Bu jiddiy tuzoq** — bilmasangiz soatlab vaqt ketadi.

Oqim rejimida tool argumentlari **bo'lak-bo'lak** keladi:
```
chunk 1: {"index":0, "function":{"name":"delive", "arguments":"{\"act"}}
chunk 2: {"index":0, "function":{"name":"ry",     "arguments":"ion\":\"ca"}}
chunk 3: {"index":0, "function":{"name":"",       "arguments":"rt_add\"}"}}
```

`index` bo'yicha lug'atga yig'ib, **matn sifatida ulab**, oxirida bir marta
`json.loads` qilinadi. Har bir bo'lakni alohida parse qilishga urinish — xato.

Qo'shimcha: `json.loads` muvaffaqiyatsiz bo'lsa **xom satr qoldiriladi**, tool
bajaruvchisi o'zi hal qiladi. Bu chidamlilik naqshi.

### T3. Ikki provayderni bitta shaklga keltirish

Ollama (`message.tool_calls`, argumentlar — obyekt) va OpenAI
(`choices[0].message.tool_calls`, argumentlar — **JSON satr**) turli formatda.
Adapter ikkalasini bitta ichki shaklga normallashtiradi.

→ Bizga to'g'ridan-to'g'ri kerak: rejada OpenAI / Gemini / OpenRouter almashadigan
adapter bor. Gemini yana uchinchi format (`functionCall`/`functionResponse`).

### T4. KV-kesh isitish (warmup) → **bulutda: prompt caching**

Ular Ollama'ni statik system prompt bilan oldindan "isitadi" — model prompt
prefiksining KV holatini keshlaydi, keyingi so'rovlar faqat farqni hisoblaydi.
Izohda: **17 s → 1 s dan kam.**

Bizda Ollama yo'q, lekin **aynan shu printsip bulutda ham bor** va bu **pul masalasi**:

Bizning system prompt + 12 ta tool sxemasi ≈ **2500–3500 token**, va u
**har bir so'rovda bir xil**. Prompt caching bilan:

| Provayder | Kesh chegirmasi | Shart |
|---|---|---|
| OpenAI | kirish tokeni **50% arzon** | ≥1024 token, avtomatik |
| Gemini | **75% gacha arzon** | aniq kesh yaratiladi |
| Anthropic | **90% arzon** | `cache_control` belgisi |

**Amaliy natija:** rejadagi xarajat jadvalidagi raqamlar **~40% kamayadi.**
Shart: statik qism (system prompt + tool sxemalari) **har doim eng boshda** turishi,
o'zgaruvchan qism (vaqt, foydalanuvchi holati) **oxirida** bo'lishi kerak.

⚠️ Bu tartibni loyihaning boshida to'g'ri qo'yish kerak — keyin o'zgartirish
qiyin bo'ladi.

### T5. Ovozli javob uchun token chegarasi

`max_tokens: 150` — ataylab past. ~100 so'z, 3-4 jumla.

Sabab: ovozda uzun javob **azob**. 500 token = ~40 soniya gapirish. Hech kim
eshitmaydi. Rejadagi «ovoz — navigatsiya, ekran — ma'lumot» qoidasining texnik
ifodasi.

→ Bizda: ovozli rejimda `max_tokens=150`, matnli rejimda `500`.

---

## 2. Ovoz kiritish (`core/stt.py`)

### T6. Gallyutsinatsiyaga qarshi: `condition_on_previous_text=False`

Whisper standart holatda oldingi matnga tayanadi va **jimlikda gap to'qib chiqaradi**
(mashhur muammo — "Subtitles by..." kabi). Bu bayroq uni o'chiradi.

→ Bizga: qaysi bulut STT ni tanlasak ham, shu turdagi sozlamani qidirish kerak.

### T7. Tezlik: `beam_size=1, best_of=1`

Greedy dekodlash — 2-3 barobar tez, aniqlik biroz past. Buyruq tanish uchun
**to'g'ri savdo** (uzun matn diktovkasi uchun emas).

### T8. VAD: `min_silence_duration_ms: 300`

300 ms jimlik = gap tugadi. Bu raqam muhim:
- Juda past (150ms) → odam nafas olganda kesib qo'yadi
- Juda yuqori (800ms) → sekin, noqulay

**300 ms — yaxshi boshlang'ich qiymat.** O'zbek tilida sinab moslash kerak.

### T9. Oqimli tanish: partial vs final

Vosk naqshi: `AcceptWaveform()` → `True` bo'lsa yakuniy natija, aks holda
`PartialResult()` — qisman matn.

→ **UX uchun muhim:** odam gapirayotganda ekranda matn **jonli chiqib boradi**.
Bu kutishni sezilarli darajada kamaytiradi (psixologik, lekin kuchli).

### T10. Transkriptni tozalash

STT chiqishida boshqaruv belgilari (`\x00-\x1f`) bo'lishi mumkin — LLM ga
yuborishdan oldin tozalanadi. Kichik, lekin unutilsa g'alati xatolar beradi.

### ❌ Rad etiladi: mahalliy modellar

`faster-whisper` va `Vosk` — modelni RAM ga yuklaydi (75–290 MB). Bitta
kompyuter uchun to'g'ri, **ko'p foydalanuvchili server uchun yaroqsiz**:
10 kishi bir vaqtda gapirsa 10 ta model nusxasi kerak.

Va **o'zbek tili sozlanmagan** — Vosk `en-us` da, Whisper `auto` da.

→ Bizda: **Mohir.ai** (bulut, o'zbek, oqimli).

---

## 3. Ovoz chiqarish (`core/tts.py`)

### T11. Sintez va ijro parallel (producer/consumer)

Ketma-ket: `sintez 1 → ijro 1 → sintez 2 → ijro 2` — har bir sintez kutiladi.
Parallel: 2-bo'lak **1-bo'lak yangrayotganda** sintez qilinadi.

Chegaralangan navbat (`maxsize=4`) — orqa bosim (backpressure): ijro sekinlashsa
sintez o'zi kutadi, xotira to'lib ketmaydi.

→ Bizda serverda: birinchi jumla audiosi klientga ketayotganda ikkinchisi
sintez qilinadi. **Sezilarli tezlik.**

### T12. Uzun pauzalarni qisqartirish

Neyron TTS tinish belgilaridan keyin 1-2 soniya jimlik qo'yadi — ovozli
suhbatda bu **juda sekin** tuyuladi. RMS bo'yicha jimlik topilib, ≤500 ms ga
kesiladi.

Ehtiyotkor qiymatlar: `threshold=0.003`, `frame=10ms`. Agressiv qilinsa
so'zlar kesiladi.

→ Aisha AI chiqishida ham tekshirish kerak. Agar pauzalar uzun bo'lsa — shu
usul (foydalanuvchi buni "AI sekin gapiryapti" deb his qiladi).

### ❌ Rad etiladi: dvigatellar

EdgeTTS / Kokoro / ElevenLabs — bizda **Aisha AI** bor va u o'zbek tili uchun
uchalasidan ham yaxshiroq. Faqat **fabrika naqshi** (config orqali dvigatel
almashish) olinadi.

---

## 4. Suhbat halqasi (`main.py`)

### T13. Gapni bo'lish — barge-in *(ovozli UX uchun hal qiluvchi)*

Foydalanuvchi AI gapirayotganda gapira boshlasa, AI **darhol** to'xtashi kerak.

Naqsh: navbatdagi barcha audio bo'laklarini **darrov bo'shatish** (drain), holatni
`LISTENING` ga o'tkazish. Shunchaki "to'xtat" yetarli emas — navbatda turgan audio
baribir yangrab ketadi.

→ **Bu bizda ham bo'lishi shart.** Ovozli assistentda gapni bo'la olmaslik —
eng ko'p shikoyat qilinadigan kamchilik. Serverda: WebSocket orqali `interrupt`
signali, server oqimni to'xtatadi, klient bufer bo'shatadi.

### T14. Vaqt konteksti in'ektsiyasi *(eslatma funksiyasi uchun SHART)*

Har bir system promptga joriy sana/vaqt qo'shiladi:

```
[JORIY SANA VA VAQT]
Hozir: Dushanba, 20-iyul 2026 — 14:35
Eslatmalar uchun aniq vaqtni shu asosda hisoblang.
```

**Nega muhim:** LLM joriy vaqtni bilmaydi. Busiz «10 daqiqadan keyin eslat»,
«ertaga soat 9 da», «shanba kuni» — hech qaysisi ishlamaydi.

→ Bizning 2-to'lqin (eslatmalar) buni **talab qiladi**. Va bu maydon o'zgaruvchan
bo'lgani uchun **promptning oxirida** turishi kerak (T4 — kesh buzilmasligi uchun).

### T15. Tegli tizim xabarlari

Suhbatga tizim voqealari **maxsus teg** bilan kiritiladi:

```
[SYSTEM_ALERT] ...      → apparat ogohlantirishi
[PROACTIVE_CHECK] ...   → sukunatdan keyin
[STARTUP_BRIEFING] ...  → ertalabki brifing
```

Promptda qat'iy qoida: **«tegni hech qachon ovoz chiqarib o'qima»**.

→ **Bizga to'g'ridan-to'g'ri kerak.** Eslatma yetib kelganda:

```
[ESLATMA] Buyurtma #4821 kuryeri 10 daqiqada yetib keladi.
Foydalanuvchiga tabiiy tilda ayting. Tegni o'qimang. Tool chaqirmang.
```

Bu — proaktiv xabarni suhbatga kiritishning **toza kanali**. Aks holda AI
tizim matnini foydalanuvchiga o'qib beradi.

### T16. Navbat chegarasi hodisasi (`turn_done_event`)

`asyncio.Event` — AI gapirib bo'lganini kutish uchun. Proaktiv xabar
**AI gapirayotganda** yuborilmasligi kerak (ustma-ust tushadi).

Naqsh: `await wait_for(turn_done, timeout=6.0)` — kutadi, lekin cheksiz emas.

### T17. Sessiyani tiklash (session resumption)

Aloqa uzilsa kontekstni yo'qotmasdan qayta ulanish.

→ Bizda bu **`AgentTask` modeli** orqali hal bo'ladi (rejada bor) — hatto
kuchliroq, chunki holat bazada, xotirada emas. Internet uzilsa ham saqlanadi.

### T18. Tool tavsiflarida buyruq ohangi *(anti-gallyutsinatsiya)*

```
"Always call this tool — never just say you opened it."
```

Bu qo'shimcha gap **muhim**. Modellar ba'zan tool chaqirmasdan «bajardim» deb
javob beradi — bu eng xavfli xato turi.

→ Bizda har bir yozish tool'i tavsifiga shunga o'xshash gap qo'shiladi:
«Bu tool'ni albatta chaqiring — buyurtma qildim deb aytishning o'zi yetarli emas.»

### T19. «Jim» tool javobi

`{"result": "ok", "silent": true}` — tool bajarildi, lekin AI bu haqda
gapirmaydi (masalan xotiraga yozish).

→ Bizda: `save_preference`, `log_view`, analitika — jim bajariladi.

---

## 5. System prompt uslubi (`core/prompt.txt`)

Bor-yo'g'i **45 qator**, lekin zich. Olinadigan qoidalar:

### T20. «Bir marta chaqirish» qoidasi
```
One-Call Policy: Never guess. Call tools exactly once. No retries.
```
Modellar noaniqlikda bir tool'ni qayta-qayta chaqirishga moyil. Bizda bu
**pul ketadigan** joyda halokatli (ikki marta buyurtma!).

→ Rejadagi `PendingAction` + idempotentlik buni allaqachon qamraydi, lekin
promptda ham bo'lishi kerak — ikki qavatli himoya.

### T21. Javob uzunligini vazifaga moslash
```
Length: Match response length to the task. Briefing = short. Complex = thorough.
```

### T22. Tool marshrutlash qoidalari — aniq va qisqa
```
computer_settings: ALL single OS actions (volume, brightness, wifi, power).
agent_task: ONLY for complex, multi-step planning (3+ steps).
Do not call agent_task while you can accomplish it with a tool
```

Bizning 12 ta bo'lim-tool uchun **aynan shunday** marshrutlash jadvali kerak:
```
delivery: do'kon, mahsulot, savat, buyurtma, kuzatish — ovqat va tovar bilan bog'liq HAMMA narsa
booking:  to'yxona, zal, xizmat, usta — vaqt band qilish
taxi:     faqat transport
places:   faqat MANZIL/joy topish (buyurtmasiz)
```

⚠️ Chegaralarni aniq yozish shart, aks holda model `places` va `delivery` ni
chalkashtiradi (ikkalasi ham do'kon qaytaradi).

### T23. Parametrlarni bitta tilda chiqarish
```
Language: Respond in user's language; extract parameters in English.
```

**Aqlli.** Model o'zbekcha javob beradi, lekin tool parametrlarini standart
shaklda beradi. Bizda: kategoriya nomlari (`pharmacy`, `restaurant`) o'zbekcha
kelmasligi kerak — `detect_category` allaqachon shunday ishlaydi.

### T24. Jim til aniqlash
Foydalanuvchi tilini birinchi marta aniqlab, **e'lon qilmasdan** xotiraga yozadi.

→ Bizda: o'zbek / rus / ingliz — profilga yoziladi, keyingi sessiyalarda
so'ralmaydi.

---

## 6. Xotira (`memory/memory_manager.py`)

Bu modul **6-to'lqin (aqllilik)** uchun tayyor qolip beradi.

### T25. Kategoriyalangan xotira
```
identity      — ism, shahar, til, yosh
preferences   — nimani yoqtiradi
projects      — faol maqsadlar
relationships — yaqinlari
wishes        — rejalari
notes         — qolgani
```

→ SamCity uchun moslashtirilgan:
```
identity      — ism, mahalla, tuman, til
preferences   — sevimli do'kon, odatiy manzil, allergiya, to'lov usuli
addresses     — "uy", "ish", "onamnikiga"  ← juda muhim
habits        — "payshanba kuni lavash", "har hafta ko'k choy"
history       — oxirgi buyurtmalar (xulosa)
```

`addresses` — bizga xos va **eng ko'p ishlatiladigani**: «uyga yetkaz» ishlashi
uchun «uy» qayerdaligini bilish kerak.

### T26. Xotira hajmi qat'iy cheklanadi *(muhim)*

`MEMORY_MAX_CHARS = 2200`. Chegara oshsa — **eng eski yozuvlar o'chiriladi**
(`updated` sanasi bo'yicha saralab).

**Nega muhim:** xotira har bir so'rovda promptga qo'shiladi. Cheklanmasa
oyiga o'sib boradi va: (a) token narxi oshadi, (b) muhim ma'lumot
"cho'kib" ketadi, (c) bir kun kontekst chegarasi portlaydi.

→ Bizda ham qat'iy chegara + eskirish siyosati bo'lishi kerak. Ko'pchilik buni
o'ylamaydi va 6 oydan keyin muammoga duch keladi.

### T27. Qiymat uzunligi cheklanadi
Bitta yozuv max 380 belgi. Model "roman" yozib yubormasligi uchun.

### T28. Promptga qo'shishda ko'rsatma
```
[WHAT YOU KNOW ABOUT THIS PERSON — use naturally, never recite like a list]
```

Busiz AI xotirani **ro'yxat qilib o'qiy boshlaydi**: «Sizning ismingiz Samandar,
shahringiz Shofirkon, sevimli do'koningiz...» — g'alati va bezovta qiluvchi.

### T29. O'zgarish bo'lmasa yozilmaydi
Har safar diskka yozish o'rniga, avval solishtiriladi. Bizda: DB yozuvi
tejaladi.

---

## 7. Proaktivlik (`actions/proactive.py`)

### T30. Ikki taymer naqshi

```
min_silence_secs = 900   # foydalanuvchi 15 daq jim tursa
check_cooldown   = 600   # ikki proaktiv xabar orasida ≥10 daq
```

**Ikkinchi taymer muhim** — busiz AI takror-takror gapirib bezor qiladi.

### T31. «Qoida emas, kontekst ber»

Fayl izohida: *"No hardcoded rules: we pass time + memory as context and Gemini
chooses."*

Ya'ni «soat 9 bo'lsa ob-havoni ayt» kabi qattiq qoida yozilmaydi — modelga
vaqt + xotira beriladi, u o'zi qaror qiladi.

→ **Bizda ehtiyot bo'lish kerak.** Bu erkin suhbat uchun yaxshi, lekin bizda
proaktiv xabar ko'pincha **aniq voqeaga** bog'langan (buyurtma yetdi, ETA 10 daq).
Ular uchun qattiq qoida **to'g'riroq** — ishonchli va bepul.

**Aralash yondashuv:**
- Voqeaga bog'liq (buyurtma, ETA, bron) → **qattiq qoida**, LLM'siz shablon
- Umumiy («payshanba, odatda lavash buyurtma qilasiz») → **LLM qaror qiladi**

---

## 8. Nima olinmaydi

| Nima | Sabab |
|---|---|
| `actions/` — 19 fayl | Kompyuter boshqarish. Serverda ma'nosiz va xavfli |
| `ui.py` (PyQt6 HUD) | Desktop oyna. Bizda web + Flutter |
| `dashboard/server.py` | Bitta foydalanuvchi, QR juftlash. Bizda Django auth |
| Mahalliy STT/TTS modellari | Ko'p foydalanuvchi uchun yaroqsiz |
| Fayl-JSON xotira + global lock | Bizda Django model + DB |
| `installer.py`, `setup.py` | Desktop o'rnatish sehrgari |

**Va eng muhimi — ularda yo'q, bizda bo'lishi shart:**

autentifikatsiya · vakolat tekshiruvi · tuman izolyatsiyasi · to'lov ·
tasdiq oqimi · audit · rate limiting · ko'p foydalanuvchi izolyatsiyasi ·
prompt injection himoyasi

Bu ro'yxat — **bizning loyihamizning eng qiyin qismi**, va Mark XLIX da
umuman yo'q (bitta odamning kompyuterida kerak emas).

---

## 9. Rejaga kiritilgan o'zgarishlar

`JARVIS_REJA.md` ga qo'shiladigan yangiliklar:

| # | O'zgarish | Qayerga |
|---|---|---|
| 1 | **Prompt caching** — statik/o'zgaruvchan qism tartibi | 0-to'lqin, arxitektura |
| 2 | Xarajat jadvali **~40% pasaytiriladi** | 2.8-bo'lim |
| 3 | **Barge-in** (gapni bo'lish) — WebSocket signali | 1-to'lqin |
| 4 | **Vaqt konteksti** in'ektsiyasi | 0-to'lqin, `prompts.py` |
| 5 | **Tegli tizim xabarlari** (`[ESLATMA]`) | 2-to'lqin |
| 6 | O'zbekcha **jumla ajratish** (son, vaqt, qisqartma) | 1-to'lqin, `stream.py` |
| 7 | Tool-call **fragment yig'ish** | 0-to'lqin, `llm.py` |
| 8 | Sintez/ijro **parallel** | 1-to'lqin, `tts.py` |
| 9 | Xotira **hajm chegarasi + eskirish** | 6-to'lqin, dizayn hozir |
| 10 | `addresses` xotira kategoriyasi («uy», «ish») | 6-to'lqin |
| 11 | Tool marshrutlash **chegaralari** jadvali | 0-to'lqin, `prompts.py` |
| 12 | «Albatta chaqiring» anti-gallyutsinatsiya gapi | 0-to'lqin |
| 13 | Proaktivlik: voqea=qoida, umumiy=LLM | 2-to'lqin |
| 14 | `max_tokens` 150 (ovoz) / 500 (matn) | 0-to'lqin |
| 15 | Jim tool javobi (`silent`) | 0-to'lqin, `registry.py` |

---

## 10. Yakuniy baho

**Kod qiymati: 0%** — litsenziya taqiqlaydi va arxitektura mos emas.

**Bilim qiymati: sezilarli** — 31 ta texnika, ulardan **4 tasi** rejadagi
haqiqiy bo'shliqlarni yopdi:

1. **Prompt caching** — xarajatni ~40% kamaytiradi *(rejada yo'q edi)*
2. **Barge-in** — ovozli UX uchun hal qiluvchi *(rejada yo'q edi)*
3. **Vaqt konteksti** — eslatma funksiyasi **busiz ishlamaydi** *(rejada yo'q edi)*
4. **Xotira eskirish siyosati** — 6 oydan keyingi muammoni oldini oladi

Qolgan 27 tasi — tasdiq va nozik sozlamalar (VAD 300ms, pauza kesish,
gallyutsinatsiya bayrog'i va h.k.). Bular kichik, lekin **aynan shu mayda
narsalar** ovozli assistentni "ishlaydi" va "yoqimli" orasida ajratadi.

**Tezlik ta'siri: ~5% emas, taxminan 15%** — asosan 0 va 1-to'lqinda,
sinov-xato bosqichini qisqartirish hisobiga.

Papkani o'chirishingiz mumkin — kerakli hamma narsa shu hujjatda.
