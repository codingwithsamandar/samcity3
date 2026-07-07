# SamCity — Rollar bo'yicha to'liq tahlil (sayt + mobil ilova)

Tahlil kodni o'rganish asosida qilindi: 8 ta Django ilova (main, delivery, taxi, booking, places, payments, notifications, api) va Flutter mobil ilova (auth/OTP, e'lonlar, ish, taksi, dostavka, bron, mahalla chat, xarita, to'lovlar, bildirishnomalar).

**Umumiy xulosa oldindan:** platforma juda keng qamrovli va ko'p rollar uchun real ish oqimlari kodda mavjud. Lekin 3 ta tizimli zaiflik hamma rolga ta'sir qiladi:
1. **SMS OTP real provayderga ulanmagan** (kod konsolga chiqadi) — productionda hech kim ro'yxatdan o'ta olmaydi.
2. **Payme/Click to'liq ulanmagan** (ServicePayment "demo" deb belgilangan) — onlayn to'lovga qurilgan barcha oqimlar (bron oldindan to'lovi, boost, pickup) hozircha qog'ozda.
3. **Push-bildirishnoma (FCM) yo'q** — WebSocket faqat ilova ochiq bo'lganda ishlaydi; kuryer/taksist/do'kon egasi yangi buyurtmani ilovani ochmaguncha ko'rmaydi.

---

## 1. E'lon qo'yuvchi (sotuvchi) rolida

**Bu sayt menga qanday foyda beradi?** Bepul e'lon joylayman (7 kategoriya: uy-joy, ish, avto, qishloq xo'jaligi, xizmat, hayvonlar), 10 tagacha rasm, xaritada joylashuv, telefon/Telegram/Instagram kontaktlari. Ko'rishlar va kontakt ochilishlar statistikasi bor — e'lonim ishlayaptimi bilaman.

**Kamchiliklari?** E'lon muddati/avtomatik yangilash yo'q. Xaridor bilan ichki chat o'rniga faqat AdInquiry (oddiy xabar ipi) — javob kelganini push orqali bilmayman. Narx kelishuvi (torg') mexanizmi yo'q.

**Foydalanishga arziydimi?** Ha — mahalliy auditoriya (Shofirkon/tuman) uchun OLX'dan ko'ra yaqinroq xaridor topaman, ayniqsa mahalla chati bilan bog'langani uchun.

**Nimaga pul to'lashga tayyorman?** Boost'ga — kodda bor va narxlari adekvat: 7 kun 10 000, 30 kun 30 000, 90 kun 75 000 so'm. Tez sotish kerak bo'lsa (mashina, uy) 30 000 so'm arzimagan pul.

**Qaysi funksiya zarar yetkazadi?** Telefon raqamim ochiq ko'rinadi — spam qo'ng'iroqlar. Raqamni yashirish/proksi-qo'ng'iroq yo'q. AdReport bilan raqobatchi e'lonimni yolg'on shikoyat qilishi mumkin — moderatsiya qanchalik adolatli, kodda avtomatik himoya yo'q.

**Nima qo'shilsa qulay bo'ladi?** E'lonni avtomatik yuqoriga ko'tarish (bump), sotuvchi reytingi (User.rating bor, lekin e'lon savdosidan baho yig'ilmaydi), "sotildi" belgisidan keyin xaridor bilan o'zaro baho.

**Yangi pullik funksiya?** "VIP sotuvchi" profili (do'kon-vitrina) — oyiga 30–50 ming so'm; e'lonni Telegram-kanalga avtomatik chiqarish — e'lon boshiga 5 000 so'm.

**Kunlik hayotga yordami?** Ha — eski buyumni tez pullash. Holati yaxshi, lekin qidiruv trendi (SearchQuery) sotuvchiga ko'rsatilmaydi — "nima qidirilyapti" ni bilsam, nimani sotishni bilardim.

**Dizayn qulaymi?** Ha — zamonaviy custom CSS (Inter shrifti, yumaloq kartalar), Leaflet xarita. Rasm yuklashda siqish/tartiblash bor (order maydoni).

## 2. E'lon oluvchi (xaridor) rolida

**Foydasi?** Kategoriya + narx + joylashuv bo'yicha qidiruv, sevimlilar (AdFavorite), xaritada yaqin e'lonlar, sotuvchiga savol yozish (AdInquiry), firibgarlikni shikoyat qilish (AdReport).

**Kamchiliklari?** Narx tarixi yo'q — qimmat yoki arzonligini bilmayman. Sotuvchi reytingi e'lon kartasida ko'rinmaydi. Saqlangan qidiruv + "yangi e'lon tushdi" ogohlantirishi yo'q — har kuni qo'lda kirib qarashim kerak.

**Foydalanishga arziydimi?** Ha — bitta ilovada e'lon + dostavka + taksi; qishloq/tuman darajasida boshqa alternativa yo'q.

**Pul to'lashga tayyorman?** Xaridor sifatida deyarli yo'q — bu to'g'ri, xaridor bepul bo'lishi kerak. Faqat "ishonchli tekshiruv" (mashina/uy hujjatini tekshirish xizmati) uchun 20–50 ming so'm to'lardim.

**Zarar yetkazuvchi funksiya?** Tekshirilmagan e'lonlar — firibgar oldindan pul so'rasa, platformada himoya (escrow faqat venue-bronda bor, oddiy savdoda yo'q).

**Nima qo'shilsa?** Saqlangan qidiruv + push; sotuvchi bilan to'liq ichki chat; narx bo'yicha saralash/filtr kengaytmasi; "shunga o'xshash e'lonlar".

**Yangi pullik funksiya?** Yo'q — xaridar uchun hammasi bepul qolsin, aks holda auditoriya qochadi.

**Kunlik hayotga yordami?** Ha, lekin bildirishnomasiz "har kuni kirib qarash" odatiga bog'liq — bu zaif nuqta.

**Dizayn?** Qulay — kartali ro'yxat, rasmlar keshlanadi (mobilda cached_network_image). Filtrlar mobilda qanchalik chuqur — cheklangan.

## 3. Ish beruvchi (ishchi olaman) rolida

**Foydasi?** JobAd to'liq: lavozim, kompaniya tavsifi, menejer ismi/telefoni, ish turi (to'liq/yarim/masofaviy/shartnoma/vaqtinchalik), maosh vilkasi, muddat (deadline), ko'rishlar soni. Rezyume bazasini (ResumeAd) ko'rib o'zim ham nomzod qidira olaman.

**Kamchiliklari?** Eng kattasi — **ariza (application) tizimi yo'q**: nomzod faqat telefon qiladi. Kim ko'rdi, kim qiziqdi — bilmayman. Nomzodlarni saralash, status yuritish (ko'rildi/suhbat/rad) yo'q. E'lonimga kelgan qo'ng'iroqlarni sanab bo'lmaydi.

**Foydalanishga arziydimi?** Ha — mahalliy oddiy kasblar (sotuvchi, haydovchi, usta) uchun tez va bepul kanal.

**Pul to'lashga tayyorman?** Ish e'lonini boost qilishga — 15–30 ming so'm/hafta. Rezyume bazasiga kengaytirilgan kirish (kontaktlarni ochish) — oyiga 50–100 ming so'm.

**Zarar?** Menejer telefoni ochiq — ishga aloqasiz qo'ng'iroqlar. Yolg'on rezyumelarni tekshirib bo'lmaydi.

**Nima qo'shilsa?** Ichki ariza tugmasi + nomzodlar ro'yxati; rezyume filtri (tajriba, mahalla bo'yicha); suhbat vaqtini booking-slot tizimi orqali belgilash (kod bazada slot tizimi tayyor — qayta ishlatsa bo'ladi!).

**Yangi pullik + qancha?** "Shoshilinch vakansiya" belgisi 20 ming so'm; nomzod bazasidan qidiruv obunasi 100 ming so'm/oy.

**Kunlik hayot?** Mavsumiy ishchi (qurilish, dala ishi) topishda juda foydali bo'lardi — lekin "bir kunlik ish" tez-topish rejimi yo'q.

**Dizayn?** Yaxshi, forma tushunarli. Mobilda jobs_screen bor — to'liq paritet.

## 4. Ish izlovchi rolida

**Foydasi?** Bepul rezyume (tajriba darajasi, ko'nikmalar, kutilayotgan maosh), ish e'lonlarini ko'rish, ish beruvchiga to'g'ridan-to'g'ri telefon/Telegram orqali chiqish. "Ishga joylashdim" statusi bor.

**Kamchiliklari?** Bir tugmali ariza yo'q — har safar qo'ng'iroq qilish noqulay va qo'rqinchli. Yangi vakansiya haqida push yo'q. Maosh bo'yicha filtr/saralash cheklangan. Rezyumega necha kishi qaraganini ko'raman (views), lekin kim qaragani noma'lum.

**Arziydimi?** Ha — mahalliy ish uchun eng tez kanal, ayniqsa rasmiy portallar qamramaydigan kasblar uchun.

**Pul to'lashga?** Rezyume boost — 10 ming so'm/hafta, ish topish davri qisqarsa arziydi. Boshqasiga yo'q — ishsiz odamdan pul olish adolatsiz va platformani o'ldiradi.

**Zarar?** Telefonim rezyumeda ochiq — firibgarlar ("avans to'lang, ish beramiz") uchun nishon. Platformada ish beruvchini tekshirish belgisi yo'q.

**Nima qo'shilsa?** "Ariza berish" tugmasi; tasdiqlangan ish beruvchi belgisi; kunlik/mardikor ish bo'limi; yangi vakansiya push'i.

**Pullik yangi funksiya?** Deyarli yo'q; ehtimol AI-rezyume yozib berish 10 ming so'm (bir martalik).

**Kunlik hayot?** To'g'ridan-to'g'ri ha. Holat o'rtacha — kontakt-only model eskirgan.

**Dizayn?** Sodda va tushunarli — bu auditoriya uchun to'g'ri tanlov.

## 5. Taksist rolida (biznes rol — qo'shimcha savollar bilan)

**Foydasi?** Taxist profili: A→B marshrutlar (Route), mashina modeli, tashilgan yo'lovchilar soni, reyting va sharhlar (TaxistReview), real-vaqt joylashuv uzatish (WebSocket), Trip (safar) va Payment yozuvlari. Mijoz meni xaritada ko'radi — ishonch ortadi.

**Kamchiliklari?** Buyurtma taqsimoti (dispatch) avtomatik emas — Uber-uslub "yaqin haydovchiga taklif" logikasi ko'rinmaydi. Push yo'qligi kritik: ilova ochiq turmasa buyurtmani o'tkazib yuboraman. Kunlik daromad hisoboti/statistika paneli yo'q.

**Nega shartnoma qilaman?** Bekatda kutib o'tirish o'rniga onlayn oqim olish uchun. Reyting va sharh to'plash — doimiy mijoz bazasi degani.

**Daromadni oshiradimi?** Boshida +10–20% (yangi mijozlar), lekin faqat push va adolatli taqsimot bo'lsa. Aks holda vaqtimni oladi, foyda bermaydi.

**Qancha to'layman?** Safardan 5–10% komissiya — maksimum. Yoki oylik obuna 50–100 ming so'm (komissiyasiz) — menga obuna afzal, hisob-kitob shaffof.

**Nega joyimni kiritaman?** Marshrutim (masalan Shofirkon→Buxoro) qidiruion chiqishi uchun — bu mening vitrinam.

**Vaqtimni oladimi?** Profil to'ldirish 15 daqiqa. Keyin faqat "bo'shman/bandman" tugmasi. Maqbul.

**Daromadga ishonamanmi?** Yarim ishonaman: mijoz oqimi mahalla chati orqali kelsa — ha. Lekin SMS/push ishlamaguncha real buyurtma aylanishiga ishonmayman.

**Zarar?** Past baho/yolg'on sharh — apellyatsiya mexanizmi yo'q. Joylashuvim doim ko'rinib turishi — xavfsizlik masalasi, "faqat faol safarda ko'rsatish" kerak.

**Dizayn?** Haydovchi paneli oddiy; mobilda taxists_screen/my_trips bor — yetarli.

## 6. Taksi topuvchi (yo'lovchi) rolida

**Foydasi?** Ikki yo'l: (1) dispetcher xizmatlar katalogi (1265 kabi qisqa raqamlar, boshlang'ich narx + km narxi, 5 km uchun namuna narx, sharhlar) — qo'ng'iroq qilib chaqiraman; (2) AB-taksistlar ro'yxati — marshrut bo'yicha haydovchi tanlab, reytingini ko'rib bog'lanaman. Safarni xaritada kuzatish (trip_track) bor.

**Kamchiliklari?** Ilova ichidan bir tugma bilan buyurtma berish oqimi to'liq emas — asosan telefon-qo'ng'iroq modeli. Narx oldindan aniq hisoblanmaydi (faqat namuna). Haydovchi kelish vaqti (ETA) yo'q.

**Arziydimi?** Ha — barcha taksi variantlari bir joyda, narxlarni solishtirish imkoni bu hududda noyob.

**Pul to'lashga?** Yo'q, yo'lovchi to'lamasligi kerak. Faqat "rejali safar broni" (ertaga 6:00 da Buxoroga) kafolati uchun 5–10 ming so'm depozit to'lardim.

**Zarar?** Tekshirilmagan haydovchi — hujjat/tex-ko'rik tasdig'i platformada yo'q. Baholar kam bo'lganda reyting aldamchi.

**Nima qo'shilsa?** Onlayn buyurtma + avtomatik eng yaqin haydovchi; taxminiy narx kalkulyatori (base_price + km — kod bor, marshrutga ulash kifoya); safarni yaqinlarim bilan ulashish (live location share).

**Pullik yangi?** Yo'q.

**Kunlik hayot?** Ha — tumanlararo qatnovda har kuni kerak. Holati: katalog sifatida yaxshi, buyurtma tizimi sifatida chala.

**Dizayn?** Xizmat kartalari (narx, reyting) tushunarli. Yaxshi.

## 7. Taksi xizmati (dispetcher kompaniya, masalan "1265") boshlig'i rolida — biznes

**Nega shartnoma qilaman?** Raqamim katalogda chiqadi, narxlarim raqobatchilar yonida ko'rinadi, sharhlar orqali obro' yig'aman. Reklama byudjetimning bir qismi shu yerga o'tishi mantiqli.

**Foydasi?** Bepul vitrina + haydovchilarimni (Taxist.service orqali) profilimga bog'lash. Mijoz 5 km narxni ko'rib, telefonim shundoq yonida — konversiya yuqori.

**Daromadga ta'siri?** Oshiradi, chunki qo'ng'iroqlar soni ortadi. Pasaytirish xavfi: raqobatchi narxi mendan past bo'lsa, ochiq taqqoslash mijozni olib ketadi — lekin bu bozor, adolatli.

**Qancha to'layman?** Katalogda ustun joy (top-listing) uchun oyiga 100–200 ming so'm. Foiz bermayman — buyurtma platforma orqali emas, telefonim orqali kelgani uchun foizni o'lchab bo'lmaydi.

**Nega ma'lumotimni kiritaman?** Kiritmasam raqobatchim kiritadi va mijozlar o'shani ko'radi.

**Vaqt oladimi?** Deyarli yo'q — bir marta to'ldiriladi, faqat narx o'zgarganda yangilanadi.

**Daromadga ishonch?** Ha, ishonaman — bu model (katalog + qo'ng'iroq) allaqachon ishlaydigan odatga tayanadi, internetga yangi odat o'rgatmaydi. Eng past riskli rol shu.

**Kamchilik/xavf?** Yolg'on 1★ sharhlar (raqobatchi yozishi mumkin) — sharhga faqat real Trip qilganlar yoza olishi kerak, hozir unique_together(service,user) bor lekin safar sharti yo'q.

## 8. Katta do'kon / yetkazib berish do'koni egasi rolida — biznes

**Foydasi?** To'liq e-commerce: do'kon profili (logo, galereya 6 rasm, ish vaqti), mahsulotlar (narx, ombor/stock, "tugadi — qachon keladi" taymeri), buyurtmalar paneli (9 bosqichli status: kutilmoqda→qabul→tayyorlanmoqda→tayyor→haydovchi→yo'lda→yetkazildi), StoreUpdate (yangilik e'lon qilish), obunachilar (StoreSubscription), mijoz bilan chat (StoreChatThread).

**Kamchiliklari?** Do'kon chati "skeleton" — real-time push ulanmagan (kodda TODO). Ko'p xodimli boshqaruv yo'q (faqat owner javob beradi, StoreStaff TODO). Savdo analitikasi (kunlik tushum, top mahsulot) paneli ko'rinmaydi. Chegirma/aksiya moduli yo'q.

**Nega shartnoma qilaman?** Yangi savdo kanali: mahalladagi va tumandagi mijozlar telefonda buyurtma qiladi, kuryer tarmog'i tayyor. O'z kuryerimni yollamayman.

**Daromadga ta'siri?** Oshiradi — offline mijozlarga +onlayn oqim. Xavf: naqd to'lov ustunligida (kodda cash bor) buyurtmadan voz kechishlar (otkaz) zarar keltiradi.

**Qancha to'layman?** Buyurtmadan 5–8% komissiya normal (Uzum/Express24 15–25% oladi — undan ancha arzon bo'lsa o'taman). Yoki oylik 200–300 ming so'm fiks. Boshida 3 oy bepul bo'lmasa, riskka kirmayman.

**Nega do'konimni kiritaman?** Obunachi bazasi — StoreUpdate orqali aksiyalarimni to'g'ridan-to'g'ri mijoz telefoniga yuboraman, bu Instagram'dan samaraliroq (lokal auditoriya).

**Vaqt oladimi?** Ha, sezilarli: mahsulot kiritish, stock yangilash, buyurtma tasdiqlash — kuniga 1–2 soat. Kichik jamoaga og'ir; Excel-import bo'lsa yengillashardi.

**Daromadga ishonch?** Shartli: kuryerlar yetarli va push ishlasa — ha. Buyurtma 30 daqiqada tasdiqlanmasa mijoz qaytib kelmaydi, push'siz esa men buyurtmani ko'rmay qolaman. Hozirgi holatda — 50/50.

**Zarar?** Stock noto'g'ri bo'lsa (tugagan mahsulot sotilsa) obro' ketadi; restock-taymer yaxshi yechim, lekin avto-sinxron (kassa tizimi bilan) yo'q.

**Nima qo'shilsa + pullik?** Chegirma/promokod moduli (shart!), savdo analitikasi — analitika uchun oyiga 50–100 ming so'm to'lardim; mahsulotlarni Excel'dan yuklash.

**Dizayn?** Boshqaruv paneli funksional; mobilda my_stores_screen bor — do'konni telefondan boshqarish mumkin, bu katta plus.

## 9. Kuryer / dostavkachi rolida — biznes

**Foydasi?** DeliveryDriver profili (transport turi: piyoda/velo/moto/avto), "bo'shman" tugmasi, tayyor buyurtmalar ro'yxatidan olish (status='ready', driver=null indeksi bor — panel tez), GPS-joylashuvim mijozga jonli ko'rinadi (DriverLocation, heading/speed bilan), haydovchi dashboard.

**Kamchiliklari?** **Daromad moduli umuman yo'q** — delivery_fee kimga tegishi, kunlik hisob-kitob, to'lov tarixi kodda ko'rinmaydi. Bu rol uchun eng katta bo'shliq. Buyurtmani rad etish/vaqt limiti qoidalari yo'q. Push yo'q — "yangi buyurtma" ni ko'rish uchun ekranga qarab o'tirishim kerak.

**Nega shartnoma qilaman?** O'z transportim bilan qo'shimcha daromad; buyurtmalar bir oqimda, mijoz qidirmayman.

**Daromadga ta'siri?** Buyurtma oqimi barqaror bo'lsa oshiradi. Lekin hisob-kitob shaffof bo'lmasa (hozir tizimda yo'q!) ishlamayman.

**Qancha beraman?** Yetkazish haqidan 10–15% platformaga — ko'pi bilan. Yoki kuryer obunasi 30–50 ming so'm/oy.

**Vaqt oladimi?** Ish vaqtimning o'zi shu — savol emas. Muhimi: bo'sh yugurishlar (buyurtma bekor bo'lsa kompensatsiya yo'q).

**Ishonch?** Hozircha yo'q — daromad paneli bo'lmagani uchun bu tizimda "ishchi" emas, "ko'ngilli"man. Daromad moduli + push qo'shilsa ishonaman.

**Zarar?** GPS doim yoqiq — batareya + maxfiylik; faqat faol buyurtmada uzatilsin. Mijoz baholamasligi — yaxshi ishlaganim hisobga olinmaydi (kuryer reytingi yo'q).

**Nima qo'shilsa?** Kuryer hamyoni/kunlik hisobot (kritik), marshrutlash (bir yo'nalishdagi 2-3 buyurtmani birlashtirish), kuryer reytingi va bonuslar.

**Dizayn?** Driver dashboard sodda — haydash paytida katta tugmalar kerak, mavjud dizayn bunga yaqin.

## 10. Turist / mehmon rolida

**Foydasi?** Places moduli: xaritada diqqatga sazovor joylar, sharh va baholar (PlaceReview), sevimlilar, "yaqinimdagilar" (nearby). Yonida taksi katalogi va kafe/restoran broni — mehmon uchun to'liq to'plam.

**Kamchiliklari?** Faqat o'zbek tilida — chet ellik turist uchun yopiq eshik (i18n yo'q). Ro'yxatdan o'tish faqat +998 telefon bilan — xorijiy raqam bilan kira olmayman. Marshrut tuzish ("bir kunlik sayohat rejasi") yo'q. Joylar tavsifi qisqa, audio-gid yo'q.

**Arziydimi?** Mahalliy sayohatchi (boshqa tumandan kelgan) uchun ha; xorijlik uchun hozircha yo'q.

**Pul to'lashga?** Gid xizmatini bron qilish bo'lsa — kuniga 200–500 ming so'm gidga, platformaga 10%.

**Zarar?** Eskirgan ma'lumot (yopilgan joy ochiq deb tursa) — ishonch ketadi.

**Nima qo'shilsa?** Ingliz/rus tili, email-login, tayyor marshrutlar, joylarda ish vaqti + kirish narxi maydonlari.

**Kunlik hayot?** Turist uchun "safar davri" xizmati — shu davrda juda foydali.

**Dizayn?** Xarita chiroyli ishlangan (custom popup'lar), mobilda flutter_map bilan bir xil tajriba — yaxshi.

## 11. Mahalla aholisi rolida

**Foydasi?** Bu platformaning yuragi: mahalla chati (ovozli xabar, rasm, fayl, javob/forward, reaksiyalar, tahrirlash), rasmiy e'lonlar (suv/svet o'chishi!), rais'ga murojaat (CitizenRequest — holatini kuzataman: yuborildi→ko'rilmoqda→hal qilindi), so'rovnomalar (Poll), yordam markazi (qon topshirish, yo'qolgan-topilgan, keksalarga yordam, xayriya — HelpRequest + ko'ngillilar), mahalla do'konlari, kommunal to'lov daftari.

**Kamchiliklari?** Chatga kirish admin tasdig'ini kutadi (is_approved) — tasdiq kechiksa, odam sovib qoladi. Kommunal to'lov (UtilityPayment) — bu faqat qo'lda yoziladigan daftar, haqiqiy to'lov emas (chalg'itadi). Suv/svet e'loni push bo'lmasa o'z vazifasini bajarmaydi.

**Arziydimi?** Ha, eng ko'p shu rolga arziydi — mahalla guruhlari hozir Telegramda tartibsiz; bu yerda e'lon, murojaat, so'rovnoma rasmiy va izli.

**Pul to'lashga?** Yo'q, va bu to'g'ri. Fuqarolik xizmatlari bepul bo'lishi shart.

**Zarar?** Anonim bo'lmagan so'rovnomada qo'shnilar oldida ochiq ovoz berish — bosim; yaxshiyamki is_anonymous bor, default yoqilsin. Chat mojarolari — moderatsiya (ban) bor, yetarli.

**Nima qo'shilsa?** Suv/svet e'lonlari uchun SMS-fallback (keksa odamlarda smartfon yo'q); mahalla taqvimi (to'y, hashar, yig'ilish); haqiqiy kommunal to'lov integratsiyasi.

**Kunlik hayot?** Ha — bu modul kunlik hayotga eng yaqini. Holati yaxshi, faqat yetkazish (push/SMS) oqsoqlaydi.

**Dizayn?** Chat Telegram'ga o'xshash — o'rganish shart emas. To'g'ri qaror.

## 12. Mahalla do'koni egasi rolida — biznes

**Foydasi?** StoreRequest orqali ariza beraman, admin tasdiqlagach mahalla sahifasida do'konim chiqadi. Faqat pickup (olib ketish) — mijoz oldindan to'lab, kelib oladi. Mahalla obunachilariga yangilik yuboraman. Katta delivery-do'konlar bilan bitta ro'yxatda raqobatlashmayman — o'z mahallamda yakkaman.

**Kamchiliklari?** Pickup to'lovi Payme/Click'ga bog'liq — u ishlamaguncha "oldindan to'lash" ishlamaydi, demak butun model qog'ozda. Pickup ish oqimi ham kodda TODO (UI ulanmagan). Yetkazib berish opsiyasi yo'q — qo'shni ko'chaga ham olib borolmayman.

**Nega shartnoma qilaman?** Mahallamdagi 200–500 xonadon — mening butun bozorim. Ular kechqurun "nonushtaga nima bor" deb ko'rsa, ertalab kelib oladi.

**Daromadga ta'siri?** Ozgina oshiradi (+5–10%) — asosiy savdo baribir peshtaxtada. Lekin "band qilib qo'yish" (tovar ushlab turish) doimiy mijozni mustahkamlaydi.

**Qancha to'layman?** Ko'pi bilan oyiga 30–50 ming so'm fiks. Foiz berolmayman — marja past (non, sut savdosida 10% marjadan foiz bersam, o'zim yutqazaman).

**Nega kiritaman?** Qo'shni do'kon kiritsa, mijoz o'sha yerdan band qiladi.

**Vaqt oladimi?** Ha, bu og'riqli: har mahsulot narxi/qoldig'ini telefondan yangilash — kichik do'kon uchun odat emas. Soddalashtirilgan rejim kerak ("bor/yo'q" tugmasi, narxsiz).

**Ishonch?** O'rtacha. Mahalla chati bilan bog'langani ishontiradi (trafik tayyor), to'lov ishlamasligi ishontirmaydi.

**Dizayn (panel)?** mahalla_store_panel mobilda bor — telefondan boshqarish to'g'ri o'ylangan, chunki mahalla do'konchisida kompyuter yo'q.

## 13. Mahalla raisi (hokimi) rolida — boshqaruv

**Foydasi?** Rasmiy e'lon kanali (NeighborhoodAnnouncement), murojaatlar paneli (kategoriya: yo'l, suv, svet, gaz, tozalik, yoritish, obodonlashtirish; holat zanjiri bilan javob berish), so'rovnoma o'tkazish, chat moderatsiyasi (a'zo tasdiqlash, ban, anonim admin), mahalla pasporti (aholi soni, chegara xaritada poligon bilan).

**Kamchiliklari?** Statistika paneli yo'q: nechta murojaat ochiq, o'rtacha hal qilish vaqti, kategoriya kesimi — hisobot uchun kerak (yuqoriga hisobot beraman!). Murojaatni mas'ulga biriktirish (suv bo'yicha — suvchi) yo'q. SMS-ogohlantirish yo'q.

**Nega shartnoma qilaman / kiritaman?** Aholi bilan aloqa hujjatlashadi: "murojaat qildim — javob yo'q" degan gapga tizimdagi izlar javob bo'ladi. Yig'ilishga chiqmaganlar so'rovnomada ovoz beradi — qamrov ortadi.

**Daromad?** Menga daromad emas, KPI: hal qilingan murojaatlar soni va tezligi. Bu tizim KPI'ni yaxshilaydi va isbotlaydi.

**Qancha to'lardim?** Mahalla byudjetidan yoki tuman hokimligi markazlashgan holda — mahalla boshiga oyiga 100–200 ming so'm dasturiy xizmat sifatida real.

**Vaqt oladimi?** Ha — murojaatlarga javob yozish majburiyat yaratadi. Lekin bu vaqt baribir sarflanardi (qog'ozda); bu yerda tezroq.

**Ishonch?** Ha — bu modul to'liq va puxta yozilgan (holat o'tishlari CITIZEN_REQUEST_TRANSITIONS bilan qat'iy nazorat qilingan).

**Zarar?** Hal qilinmagan murojaatlar ommaga ko'rinadigan bo'lsa — bosim vositasi. Ko'rinish sozlamalari aniq bo'lishi kerak.

**Nima qo'shilsa?** Murojaatlar statistikasi/eksport (Excel), mas'ulga biriktirish, muddat (SLA) eslatmalari.

**Dizayn?** Boshqaruv katta yoshli rais uchun soddaroq bo'lishi kerak — hozirgisi o'rtacha, katta shrift rejimi foyda qilardi.

## 14. Bron qilinadigan joy egasi (sartaroshxona, salon, to'yxona, restoran, sport zal) rolida — biznes

**Foydasi?** Venue tizimi kuchli: vaqt-slotlar (30 daqiqalik, ish vaqtimga mos), ustalar ro'yxati (VenueStaff — mijoz aynan "Akmal aka"ga yoziladi), xizmatlar narxnomasi (VenueService), oldindan to'lov talabi (prepay_required), kelmaganlar uchun jarima (max 15% — qonuniy cheklangan), kutish vaqti (grace 15 daqiqa), to'yxona uchun kunlik narx. Escrow modeli: pul platformada ushlanadi (held), xizmatdan keyin menga o'tadi (released).

**Kamchiliklari?** Hammasi to'lovga bog'liq — Payme/Click ulanmagach prepay ishlamaydi, demak no-show himoyam yo'q. Takroriy mijoz bazasi (CRM): kim necha marta kelgan, ko'rinmaydi. Ustalar ish haqi hisobi yo'q. Kalendar-ko'rinish (haftalik band/bo'sh jadval) qay darajada — slot ro'yxati bor, vizual kalendar savol.

**Nega shartnoma qilaman?** Telefon jurnalim o'rniga tizim: ikki mijozni bitta vaqtga yozib yuborish xatosi yo'qoladi, kelmaganlardan jarima olaman (hozir umuman ololmayman).

**Daromadga ta'siri?** Oshiradi: (1) bo'sh slotlar onlayn to'ladi, (2) no-show kamayadi (jarima qo'rqitadi), (3) yangi mijozlar kelib qo'shiladi. Sartaroshxonada no-show 10–20% — buning yarmi qaytsa ham katta pul.

**Qancha to'layman?** Har bron uchun 1 000–2 000 so'm yoki daromaddan 3–5%. To'yxona uchun bron boshiga 50–100 ming so'm ham normal (chek katta). 15%dan ortiq so'ralsa — chiqib ketaman, telefonga qaytaman.

**Nega joyimni kiritaman?** Yangi avlod mijoz telefon qilmaydi — yozilgisi keladi. Raqobatchim tizimda bo'lsa, shanba kuni to'la, men bo'shman.

**Vaqt oladimi?** Boshida ha (xizmatlar, ustalar, ish vaqtini kiritish), keyin aksincha vaqt tejaydi — telefon jiringlashi kamayadi.

**Ishonch?** Ha — bu loyihaning eng puxta o'ylangan biznes-moduli (N+1 so'rovlargacha optimallashtirilgan, jarima limiti, grace period). To'lov ulansa darhol ishlataman.

**Zarar?** Yolg'on bronlar (to'lovsiz rejimda) jadvalimni band qilib qo'yadi — to'lovsiz bron uchun telefon-tasdiq bo'lsin. Sharh bombasi xavfi bor.

**Nima qo'shilsa + pullik?** SMS-eslatma mijozga (bron oldidan 2 soat) — buning uchun SMS boshiga 100–200 so'm to'lardim, no-show'ni yana kamaytiradi; doimiy mijoz chegirmalari; ustalar KPI paneli.

**Dizayn?** Slot tanlash oqimi mobilda (venue_book_screen) bor — mijoz uchun qulay; egasi paneli ham soddaligicha qolsin.

## 15. Bron qiluvchi mijoz rolida

**Foydasi?** Sartaroshga navbat kutmayman — usta va vaqtni tanlab yozilaman; to'yxonani sanasi bo'yicha ko'raman; bekor qilish siyosati oldindan aniq (moslashuvchan/o'rtacha/qattiq — necha foiz qaytishi yozilgan); pulim escrow'da — xizmat bo'lmasa qaytadi.

**Kamchiliklari?** Eslatma push/SMS yo'q — bronni unutib, jarima to'lash xavfi menda. Ustaning portfoliosi (ishlari rasmi) yo'q — kimga yozilayotganimni bilmayman. Onlayn to'lov ishlamasa bron shunchaki "so'rov" bo'lib qoladi.

**Arziydimi?** Ha — navbat kutish o'rniga aniq vaqt; bu shahar hayotида real ehtiyoj.

**Pul to'lashga?** Xizmat narxining o'zi yetarli; qo'shimcha to'lov to'lamayman. Bekor qilish jarimasi (max 15%) — adolatli, roziman.

**Zarar?** Jarima mexanizmi men tomonda: joy egasi kelmasa/yopiq bo'lsa menga kompensatsiya bormi? Kodda ega tomonidan bekor qilish uchun ham cancelled_by bor — lekin egaga jarima ko'rinmaydi. Bir tomonlama.

**Nima qo'shilsa?** Bron eslatmasi (kritik), usta portfoliosi va reytingi, takroriy bron ("o'tgan safargidek") tugmasi.

**Kunlik hayot?** Ha — sartarosh, salon oylik odat. Holati: oqim yaxshi, yetkazish (eslatma) chala.

**Dizayn?** Slot tugmalari, sana tanlash — tushunarli. Yaxshi.

## 16. Ota-ona (bog'cha/kurs/maktab to'lovchisi) rolida

**Foydasi?** Payments moduli: muassasalar katalogi (davlat/xususiy bog'cha, kurslar, maktab-litsey), belgilangan summa yoki erkin summa, to'lov tarixi (Transaction). Davlat bog'chasi faqat ma'lumot uchun — to'g'ri chegara.

**Kamchiliklari?** Bu modul ochiq "demo" (kodda yozilgan) — karta to'lovi haqiqiy o'tmaydi. Oylik avtomatik to'lov/eslatma yo'q. Kvitansiya/chek PDF yo'q — bog'chaga isbot kerak bo'ladi.

**Arziydimi?** To'lov real ishlaganda — ha, navbat va naqd pul tashishdan qutulaman.

**Pul to'lashga?** Xizmat haqi sifatida to'lov boshiga 500–1 000 so'm komissiyaga chidayman, undan ortiq bo'lsa naqd to'layman.

**Zarar?** "To'ladim" deb o'ylab, aslida demo-yozuv bo'lsa — jiddiy muammo. Modul ishga tushguncha uni interfeysda yashirish kerak.

**Nima qo'shilsa?** Real to'lov, oylik eslatma, chek PDF, farzand bo'yicha to'lovlar tarixi.

**Dizayn?** Kategoriya kartalari sodda — yaxshi.

## 17. Yordam so'rovchi / ko'ngilli (community) rolida

**Foydasi?** Qon kerak bo'lganda, kimdir yo'qolganda, keksa qo'shniga yordam kerakda — e'lon beraman, ko'ngillilar (HelpVolunteer) yozіladi, "favqulodda" belgisi ro'yxat tepasiga chiqaradi. Bu ijtimoiy modul platformaga jon kiritadi.

**Kamchiliklari?** Favqulodda e'lon push'siz — "qon kerak" xabari 3 soatdan keyin o'qilsa kech. Ko'ngillining ishonchliligi tekshirilmaydi.

**Pul?** Yo'q — bu bepul bo'lishi shart. Xayriya (donation) kategoriyasida to'lov integratsiyasi (ehson yig'ish) bo'lsa — foydali, lekin ehtiyotkorlik bilan (suiiste'mol xavfi).

**Nima qo'shilsa?** Favqulodda push/SMS (eng muhimi), qon guruhi bo'yicha donor bazasi (ixtiyoriy ro'yxat).

## 18. Platforma admini rolida — boshqaruv

**Foydasi?** Django admin + rol tizimi (user/business/driver/admin), shikoyatlar (AdReport, is_resolved), do'kon arizalari (StoreRequest tasdiqlash), mahalla adminlarini tayinlash, analitika (is_staff uchun panel bor), seed-komandalar (demo ma'lumot), OpenAPI hujjat, healthcheck'lar, Sentry ulagichi, Docker-stack.

**Kamchiliklari?** Kontent moderatsiyasi qo'lda — e'lon oqimi o'ssa ulgurmayman (so'z-filtr ham yo'q). Moderator roli alohida yo'q (admin=hamma narsa). Foydalanuvchini bloklash oqimi (ogohlantirish→vaqtinchalik→doimiy) yo'q.

**Ishonch/xavf?** SECURITY_AUDIT o'tkazilgan (SQLi/XSS/CSRF toza, JWT to'g'ri) — yaxshi baza. Lekin `.env`/SECRET_KEY tarixi bo'yicha audit talab qilgan amallar (kalit almashtirish) bajarilganini tekshirish kerak.

---

## Mobil ilova (Flutter) — alohida baho

**Bor narsalar:** barcha asosiy modullar sayt bilan paritetda — OTP-login, e'lonlar (+qo'shish, rasm bilan), ish/rezyume, taksi (haydovchi tafsiloti, safarlarim), dostavka (do'konlar, savat, buyurtmalarim, do'kon chati), bron (joylar, slot tanlash, bronlarim), mahalla (chat WebSocket, do'kon paneli), community, xarita (flutter_map — saytdagi Leaflet bilan bir xil OSM), to'lov varag'i (Payme/Click URL + deep link `samcity://payment-success`), bildirishnomalar (WebSocket qo'ng'iroqchasi), profil. Arxitektura toza: Riverpod + go_router + dio + secure storage (JWT).

**Kamchiliklari:**
- **FCM/APNs push yo'q** — bildirishnoma faqat ilova ochiq bo'lganda (WebSocket). Kuryer, taksist, do'kon egasi rollari uchun bu ilovani "ishlamaydigan" qiladi.
- Offline rejim yo'q — internet uzilsa (qishloq sharoiti!) hech narsa ko'rinmaydi; kesh-qatlam kerak.
- iOS build sozlamalari bor, lekin App Store talablari (birinchi navbatda push, sign in) tekshirilmagan.
- Bitta til; tema — qorong'i (#0E1525) asosiy, yorug' rejim bormi — aniq emas.
- Versiya yangilash majburlash (force update) mexanizmi yo'q — eski API bilan sinishlar bo'ladi.

**Dizayn:** zamonaviy, qorong'i tema yosh auditoriyaga mos; lekin platforma auditoriyasining katta qismi — keksa mahalla aholisi va do'konchilar. Katta shrift/yorug' rejim va soddalashtirilgan "lite" ko'rinish kerak.

---

## Yakuniy xulosa — ustuvorliklar (barcha rollar kesimida)

**Hammani to'xtatib turgan 3 ta ish (bularsiz launch bo'lmaydi):**
1. Real SMS-provayder (Eskiz/PlayMobile) — ro'yxatdan o'tish ishlashi uchun.
2. Payme/Click'ni jonli ulash — bron prepay, boost, pickup, kurs to'lovlari hammasi shunga qarab turibdi.
3. FCM push — kuryer/taksist/do'kon egasi buyurtmani real vaqtda ko'rishi uchun.

**Pul to'lashga tayyor rollar (monetizatsiya tartibi):**
1. Venue egalari — bron boshiga to'lov/3–5% (modul tayyor, eng oson start)
2. E'lon boost — narxlar allaqachon kodda (10/30/75 ming so'm)
3. Katta do'konlar — 5–8% komissiya yoki oylik fiks
4. Taksi xizmatlari — top-listing 100–200 ming so'm/oy
5. Ish beruvchilar — vakansiya boost + rezyume bazasi obunasi

**Pul olib bo'lmaydigan rollar (bepul qolsin):** xaridor, ish izlovchi, yo'lovchi, mahalla aholisi, yordam so'rovchi — bular auditoriya, mahsulot emas.

**Eng katta funksional bo'shliqlar:** kuryer daromad hisobi, ish arizasi tizimi, saqlangan qidiruv + ogohlantirish, bron eslatmalari, do'kon analitikasi, ko'p tillilik.

**Eng kuchli tomonlar:** mahalla moduli (chat + murojaat + so'rovnoma + yordam — noyob kombinatsiya), booking moduli (jarima/escrow/slot — professional daraja), delivery holat mashinasi va jonli kuzatuv, xavfsizlik bazasi (audit o'tgan), mobil paritet.

