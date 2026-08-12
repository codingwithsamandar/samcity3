"""SamCity — sayt funksiyalari bo'yicha bilimlar bazasi (FAQ / qo'llanma).

Bu modul foydalanuvchining "qanday ...?", "... nima?", "qayerdan ...?" kabi
savollariga javob beradi — saytdagi HAR BIR bo'lim va imkoniyat haqida. Har bir
yozuv: kalit iboralar (matndan izlanadi), sarlavha, tushuntirish va tegishli
havolalar (URL nomi orqali, chaqirilganda reverse qilinadi).

engine.py avval eng yaqin joyni tekshiradi, keyin shu bazani qidiradi. Shu sabab
"eng yaqin dorixona" (joy topish) va "e'lon qanday joylayman" (qo'llanma) to'g'ri
ajratiladi.
"""

from .engine import _norm


# Har bir yozuv:
#   keywords — matnda izlanadigan iboralar (apostrofsiz, kichik harfda emas ham
#              bo'lishi mumkin — _norm() mosl ashtiradi).
#   title    — qisqa sarlavha.
#   answer   — foydalanuvchiga tushuntirish (o'zbekcha).
#   actions  — [(label, url_name), ...] — url_name reverse() bilan ochiladi.
KB = [
    # ── E'lonlar (marketplace) ────────────────────────────────────────────────
    {
        'id': 'post_ad',
        'keywords': ['elon joylash', 'elon ber', 'elon qanday', 'qanday elon',
                     'elon qoshish', 'elon joylamoqchi', 'sotmoqchiman', 'sotmoqchi',
                     'narsa sotmoq', 'joylashtirish', 'elon berish'],
        'title': "E'lon joylash",
        'answer': ("📢 E'lon joylash uchun «E'lon joylash» tugmasini bosing, toifани "
                   "(uy-joy, avtomobil, texnika va h.k.) tanlang, rasm va narxni "
                   "kiriting. E'loningiz darhol bozorda ko'rinadi. Uni «Ko'tarish» "
                   "(boost) orqali tepaga chiqarishingiz ham mumkin."),
        'actions': [("E'lon joylash", 'ad_create'), ("Barcha e'lonlar", 'all_ads')],
    },
    {
        'id': 'boost_ad',
        'keywords': ['elon kotarish', 'boost', 'elonni tepaga', 'pullik elon',
                     'elon reklama', 'elonni kotar'],
        'title': "E'lonni ko'tarish (boost)",
        'answer': ("🚀 E'loningizni ko'proq odam ko'rishi uchun uni «Ko'tarish» "
                   "mumkin — u qidiruvda va ro'yxat tepasida ustun turadi. Buni "
                   "o'z e'loningiz sahifasidan yoki e'lonlarim bo'limidan qilasiz."),
        'actions': [("E'lonlarim", 'my_ads')],
    },
    {
        'id': 'saved_ads',
        'keywords': ['saqlangan elon', 'sevimli elon', 'favorit', 'yoqtirgan elon'],
        'title': "Saqlangan e'lonlar",
        'answer': ("❤️ Yoqqan e'lonni ❤️ tugmasi bilan saqlab qo'yishingiz va keyin "
                   "«Saqlangan e'lonlar» bo'limidan qaytadan ko'rishingiz mumkin."),
        'actions': [("Saqlangan e'lonlar", 'saved_ads')],
    },
    # ── Ish / rezyume ─────────────────────────────────────────────────────────
    {
        'id': 'post_job',
        'keywords': ['ish elon', 'vakansiya joylash', 'ishchi kerak', 'xodim kerak',
                     'ish beraman', 'vakansiya qoshish', 'ish orni joylash'],
        'title': "Ish e'loni (vakansiya)",
        'answer': ("💼 Xodim izlayotgan bo'lsangiz, «Ish e'loni joylash» orqali "
                   "vakansiya e'lon qilasiz. Nomzodlar rezyumelari bilan bog'lanadi."),
        'actions': [("Ish e'loni joylash", 'job_create'), ("Ish e'lonlari", 'job_list')],
    },
    {
        'id': 'post_resume',
        'keywords': ['rezyume', 'ish qidiryapman', 'ish izlayapman', 'cv joylash',
                     'ishga joylashmoqchi', 'rezyume joylash'],
        'title': "Rezyume joylash",
        'answer': ("📄 Ish qidirayotgan bo'lsangiz, rezyume joylang — ish beruvchilar "
                   "sizni topadi. «Rezyume joylash» orqali ma'lumotlaringizni kiriting."),
        'actions': [("Rezyume joylash", 'resume_create'), ("Rezyumelar", 'resume_list')],
    },
    # ── Taksi ─────────────────────────────────────────────────────────────────
    {
        'id': 'order_taxi',
        'keywords': ['taksi qanday', 'taksi buyurtma', 'taksi chaqir', 'mashina chaqir',
                     'taksi qanaqa'],
        'title': "Taksi buyurtma qilish",
        'answer': ("🚕 Taksi bo'limida narxni oldindan hisoblab, onlayn haydovchini "
                   "chaqirasiz yoki AB marshrut bo'yicha taksist tanlaysiz. Safarni "
                   "xaritada kuzatib borish mumkin."),
        'actions': [("Taksi chaqirish", 'taxi:home'), ("Xaritada taksistlar", 'taxi:map')],
    },
    {
        'id': 'become_taxist',
        'keywords': ['taksist bolish', 'haydovchi bolish', 'taksi haydovchi',
                     'taksistlikka', 'taksist royxat', 'haydovchi royxatdan'],
        'title': "Taksist bo'lish",
        'answer': ("🧑‍✈️ Haydovchi bo'lib ishlashni xohlasangiz, taksist sifatida "
                   "ro'yxatdan o'ting — mashina va marshrutlaringizni qo'shib, "
                   "buyurtma qabul qilasiz."),
        'actions': [("Taksist bo'lish", 'taxi:taxist_register')],
    },
    # ── Yetkazib berish / do'konlar ───────────────────────────────────────────
    {
        'id': 'order_delivery',
        'keywords': ['ovqat buyurtma', 'dokondan buyurtma', 'yetkazib berish qanday',
                     'mahsulot buyurtma', 'yetkazish qanday', 'buyurtma berish'],
        'title': "Do'kondan buyurtma / yetkazish",
        'answer': ("🛒 Do'konlar bo'limida do'konni tanlab, mahsulotlarni savatga "
                   "qo'shasiz va buyurtma berasiz. Ba'zi do'konlar yetkazib beradi, "
                   "ba'zilari «olib ketish» (pickup) rejimida ishlaydi."),
        'actions': [("Do'konlar", 'delivery:store_list')],
    },
    {
        'id': 'open_store',
        'keywords': ['dokon ochish', 'magazin ochish', 'dokon ochmoqchi', 'savdo dokon',
                     'mahalla dokon', 'oz dokonim', 'dokon royxat'],
        'title': "Do'kon ochish",
        'answer': ("🏪 O'z do'koningizni ochish uchun ariza qoldiring — administrator "
                   "tasdiqlagach, do'kon va mahsulotlaringizni qo'shasiz. Mahalla "
                   "do'koni faqat o'z mahallangiz sahifasida ko'rinadi."),
        'actions': [("Do'kon ochishga ariza", 'delivery:store_request_create'),
                    ("Mening do'konlarim", 'delivery:my_stores')],
    },
    {
        'id': 'delivery_driver',
        'keywords': ['kuryer bolish', 'yetkazuvchi bolish', 'delivery haydovchi',
                     'kuryer royxat', 'yetkazuvchi royxat'],
        'title': "Yetkazuvchi (kuryer) bo'lish",
        'answer': ("🏍️ Buyurtmalarni yetkazib ishlashni xohlasangiz, haydovchi "
                   "sifatida ro'yxatdan o'ting va yaqin buyurtmalarni qabul qiling."),
        'actions': [("Haydovchi bo'lish", 'delivery:driver_register')],
    },
    # ── Joylar bron (to'yxona / zal) ──────────────────────────────────────────
    {
        'id': 'book_venue',
        # Faqat "qanday bron qilaman?" (qo'llanma) savoli — umumiy bron so'zlari
        # emas. Aks holda haqiqiy to'yxona qidiruvini bosib qo'yardi.
        'keywords': ['qanday bron', 'bron qanday', 'toyxona qanday bron', 'zal qanday band',
                     'joy qanday band', 'bron qilish tartibi', 'qanday band qilaman'],
        'title': "To'yxona / zal bron qilish",
        'answer': ("📅 To'yxona, restoran yoki zalni sana va vaqtni tanlab bron "
                   "qilasiz. Xizmatlar va xodimlarni ham tanlab, oldindan to'lash "
                   "mumkin."),
        'actions': [("Joylarni bron qilish", 'venue_list')],
    },
    {
        'id': 'add_venue',
        'keywords': ['toyxona qoshish', 'zal qoshish', 'oz joyimni', 'venue qoshish',
                     'joyimni royxat'],
        'title': "O'z to'yxona/zalingizni qo'shish",
        'answer': ("🏛️ Sizda to'yxona yoki zal bo'lsa, uni qo'shib, xizmatlar, "
                   "narxlar va bo'sh vaqtlarni belgilang — mijozlar bron qiladi."),
        'actions': [("Joy qo'shish", 'venue_create')],
    },
    # ── To'lovlar ─────────────────────────────────────────────────────────────
    {
        'id': 'payments',
        'keywords': ['kommunal tolov', 'tolov qilish', 'tolash', 'payme', 'click',
                     'gaz tolov', 'suv tolov', 'svet tolov', 'internet tolov',
                     'tolovni qanday', 'hisob tolash'],
        'title': "To'lovlar (kommunal va boshqalar)",
        'answer': ("💳 To'lovlar bo'limida kommunal va boshqa xizmatlarni Payme yoki "
                   "Click orqali to'laysiz. Har bir to'lov uchun kvitansiya saqlanadi."),
        'actions': [("To'lovlar", 'payments:home'), ("To'lovlarim", 'payments:my_payments')],
    },
    {
        'id': 'utilities',
        'keywords': ['kommunal hisob', 'kommunal qoshish', 'kommunal kuzatish',
                     'kommunal royxat'],
        'title': "Kommunal hisoblarni yuritish",
        'answer': ("🧾 Kommunal to'lovlaringizni ro'yxatga olib, oyma-oy kuzatib "
                   "borishingiz mumkin."),
        'actions': [("Kommunal to'lovlar", 'utility_list')],
    },
    # ── Mahalla / hamjamiyat ──────────────────────────────────────────────────
    {
        'id': 'mahalla',
        'keywords': ['mahalla', 'mahalla bolimi', 'mahalla elon', 'mahalla xizmat',
                     'mahalla haqida'],
        'title': "Mahalla bo'limi",
        'answer': ("🏘️ Mahalla bo'limida o'z mahallangiz e'lonlari, so'rovnomalar, "
                   "xizmatlar, mahalla do'konlari va hokimlik/mahalla e'lonlarini "
                   "ko'rasiz hamda muammo bo'yicha murojaat yuborishingiz mumkin."),
        'actions': [("Mahallaga kirish", 'mahalla_home')],
    },
    {
        'id': 'polls',
        'keywords': ['sorovnoma', 'sorov ', 'ovoz berish', 'poll', 'sorovnomada'],
        'title': "So'rovnomalar",
        'answer': ("🗳️ Mahalla so'rovnomalarida ovoz berib, jamoat qarorlarida "
                   "ishtirok etasiz yoki o'zingiz so'rovnoma yaratasiz."),
        'actions': [("So'rovnomalar", 'poll_list')],
    },
    {
        'id': 'help_center',
        'keywords': ['yordam markazi', 'komak sorash', 'volontyor', 'xayriya',
                     'yordam berish', 'kongilli'],
        'title': "Yordam markazi",
        'answer': ("🤝 Yordam markazida ko'mak so'rashingiz yoki muhtojlarga volontyor "
                   "bo'lib yordam berishingiz mumkin."),
        'actions': [("Yordam markazi", 'help_list')],
    },
    {
        'id': 'citizen_request',
        'keywords': ['murojaat', 'shikoyat', 'ariza yozish', 'muammo bildirish',
                     'hokimlikka murojaat', 'murojaat yozish'],
        'title': "Murojaat / shikoyat yuborish",
        'answer': ("📝 Kommunal yoki mahalla muammosi bo'yicha murojaat (shikoyat) "
                   "yuborishingiz va uning holatini kuzatib borishingiz mumkin. Buni "
                   "o'z mahallangiz sahifasidan qilasiz."),
        'actions': [("Mahallaga o'tish", 'mahalla_home')],
    },
    # ── Xarita / joylar ───────────────────────────────────────────────────────
    {
        'id': 'map',
        'keywords': ['xarita', 'joylar royxati', 'directory', 'joylar katalog',
                     'joylarni korish'],
        'title': "Xarita va joylar",
        'answer': ("🗺️ Xaritada dorixona, shifoxona, bank, restoran, do'kon va "
                   "boshqa joylarni toifalar bo'yicha ko'rasiz, yo'nalish quramiz. "
                   "«Yaqinimdagilar» sizga eng yaqinlarini masofa bilan chiqaradi."),
        'actions': [("Xaritani ochish", 'places:map'),
                    ("Yaqin atrofdagilar", 'places:nearby')],
    },
    {
        'id': 'add_place',
        'keywords': ['joy qoshish', 'xaritaga qoshish', 'manzil qoshish',
                     'biznes qoshish', 'obyekt qoshish'],
        'title': "Xaritaga joy qo'shish",
        'answer': ("📍 O'z biznesingiz yoki foydali joyni xaritaga qo'shishingiz "
                   "mumkin — nomi, toifasi, manzili va koordinatasini kiriting."),
        'actions': [("Joy qo'shish", 'places:place_create')],
    },
    {
        'id': 'tourism',
        'keywords': ['sayohat', 'diqqatga sazovor', 'turistik', 'sayil joy',
                     'korsa arzigulik'],
        'title': "Sayohat / diqqatga sazovor joylar",
        'answer': ("🏞️ Sayohat bo'limida shahar va atrofdagi diqqatga sazovor "
                   "joylar, tabiat go'shalari va tarixiy obidalar bilan tanishasiz."),
        'actions': [("Sayohat", 'places:tourism_list')],
    },
    # ── Akkaunt / profil ──────────────────────────────────────────────────────
    {
        'id': 'register',
        'keywords': ['royxatdan otish', 'account yaratish', 'registratsiya',
                     'akkaunt ochish', 'royxatdan otmoqchi'],
        'title': "Ro'yxatdan o'tish",
        'answer': ("✅ Ro'yxatdan o'tish uchun telefon raqamingizni kiriting — SMS "
                   "(yoki Telegram) orqali kelgan kodni tasdiqlaysiz. Bepul."),
        'actions': [("Ro'yxatdan o'tish", 'register')],
    },
    {
        'id': 'login',
        'keywords': ['tizimga kirish', 'akkauntga kirish', 'parolni', 'login qilish',
                     'kira olmayapman'],
        'title': "Tizimga kirish",
        'answer': ("🔑 Telefon raqamingiz va parolingiz bilan kirasiz. «Meni eslab "
                   "qol» belgilansa, 30 kun ochiq qoladi."),
        'actions': [("Kirish", 'login')],
    },
    {
        'id': 'profile',
        'keywords': ['profil', 'mening sahifam', 'profil tahrir', 'sozlamalar',
                     'malumotlarimni ozgartir'],
        'title': "Profil va sozlamalar",
        'answer': ("👤 Profil bo'limida shaxsiy ma'lumotlaringiz, rasmingiz va "
                   "e'lonlaringizni boshqarasiz."),
        'actions': [("Profil", 'profile'), ("Tahrirlash", 'profile_edit')],
    },
    {
        'id': 'notifications',
        'keywords': ['bildirishnoma', 'xabarlar', 'notification', 'bildirishnomalar'],
        'title': "Bildirishnomalar",
        'answer': ("🔔 Buyurtma, sharh va boshqa muhim voqealar haqida "
                   "bildirishnomalar shu bo'limda to'planadi."),
        'actions': [("Bildirishnomalar", 'notification_list')],
    },
    {
        'id': 'dashboard',
        'keywords': ['boshqaruv paneli', 'dashboard', 'statistikam', 'kabinet'],
        'title': "Boshqaruv paneli",
        'answer': ("📊 Boshqaruv panelida e'lonlaringiz, buyurtmalaringiz va "
                   "faoliyatingiz statistikasini bir joyda ko'rasiz."),
        'actions': [("Boshqaruv paneli", 'dashboard')],
    },
    {
        'id': 'app',
        'keywords': ['mobil ilova', 'ilovani yuklab', 'apk yuklab', 'telefon ilova',
                     'android ilova', 'ilova bormi'],
        'title': "Mobil ilova",
        'answer': ("📱 SamCity mobil ilovasini yuklab olsangiz — tezroq, qulay va "
                   "push-bildirishnomalar bilan ishlaydi."),
        'actions': [("Ilovani yuklab olish", 'app_download')],
    },
    {
        'id': 'search',
        'keywords': ['qidiruv', 'qidirish qanday', 'izlash', 'nima qidirsam'],
        'title': "Qidiruv",
        'answer': ("🔎 Yuqoridagi qidiruv orqali e'lonlar, do'konlar va joylarni bir "
                   "joydan qidirasiz."),
        'actions': [("Qidiruv", 'global_search')],
    },
]


# Taksi moduli arxivlangan bo'lsa (settings.TAXI_ENABLED=False) shu KB
# yozuvlari javob sifatida berilmaydi — engine.py shu ro'yxatga qaraydi.
TAXI_KB_IDS = ('order_taxi', 'become_taxist')


def answer(qn):
    """Normallashtirilgan matn bo'yicha eng mos KB yozuvini qaytaradi (yoki None).

    Ball = mos kelgan kalit iboralar uzunliklari yig'indisi. Eng uzun/aniq
    moslik yutadi. Ball past bo'lsa (tasodifiy qisqa moslik) — None.
    """
    from django.conf import settings
    taxi_off = not settings.TAXI_ENABLED
    best, best_score = None, 0
    for entry in KB:
        # Taksi arxivlangan — bu yozuvlar javob sifatida qaytarilmaydi
        # (havolalari reverse qilinmaydi, xizmat ham yopiq).
        if taxi_off and entry['id'] in TAXI_KB_IDS:
            continue
        score = 0
        for k in entry['keywords']:
            kn = _norm(k)
            if kn and kn in qn:
                score += len(kn)
        if score > best_score:
            best, best_score = entry, score
    if best and best_score >= 5:
        return best
    return None


def overview_actions():
    """«Nimalar qila olasan?» uchun asosiy bo'limlarga tez havolalar.

    Taksi arxivlangan bo'lsa — taksi yorlig'i ko'rsatilmaydi.
    """
    from django.conf import settings
    items = [
        {'label': "📢 E'lon joylash", 'q': "e'lon qanday joylayman"},
        {'label': "🛒 Do'kon ochish", 'q': "do'kon qanday ochaman"},
        {'label': '💳 To\'lovlar', 'q': 'kommunal to\'lovni qanday to\'layman'},
        {'label': '🏘️ Mahalla', 'q': 'mahalla bo\'limi nima'},
        {'label': '📅 Joy bron', 'q': "to'yxona qanday bron qilaman"},
    ]
    if settings.TAXI_ENABLED:
        items.insert(1, {'label': '🚕 Taksi', 'q': 'taksi qanday chaqiraman'})
    return items
