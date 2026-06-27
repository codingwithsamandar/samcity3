"""
To'liq demo ma'lumotlar yuklash buyrug'i.
Ishlatish: python manage.py demo_data
           python manage.py demo_data --clear   (avval tozalab keyin yuklaydi)
"""
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta


class Command(BaseCommand):
    help = "Demo ma'lumotlarni bazaga yuklaydi — barcha funksiyalar uchun"

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help="Avval barcha demo ma'lumotlarni o'chiradi")

    def handle(self, *args, **options):
        from main.models import (
            User, Ad, AdImage, Neighborhood, ChatRoom, ChatMessage,
            Booking, JobAd, ResumeAd, UtilityPayment,
        )

        if options['clear']:
            self.stdout.write("🗑  Avvalgi demo ma'lumotlar o'chirilmoqda...")
            UtilityPayment.objects.all().delete()
            Booking.objects.all().delete()
            ChatMessage.objects.all().delete()
            ChatRoom.objects.all().delete()
            Neighborhood.objects.all().delete()
            ResumeAd.objects.all().delete()
            JobAd.objects.all().delete()
            Ad.objects.all().delete()
            User.objects.filter(phone__startswith='+99890').delete()
            self.stdout.write("  ✅ Tozalandi\n")

        self.stdout.write("=" * 60)
        self.stdout.write("🚀 Demo ma'lumotlar yuklanmoqda...")
        self.stdout.write("=" * 60)

        # ─────────────────────────────────────────────────────────────
        # 1. FOYDALANUVCHILAR
        # ─────────────────────────────────────────────────────────────
        self.stdout.write("\n👤 Foydalanuvchilar:")

        users_data = [
            {
                "phone": "+998901234567",
                "name": "Sardor Aliyev",
                "email": "sardor@example.com",
                "bio": "Toshkent sakini, IT mutaxassisi. Avtomobil va ko'chmas mulk sohasida faol.",
                "password": "demo1234",
                "role": "user",
            },
            {
                "phone": "+998902345678",
                "name": "Malika Yusupova",
                "email": "malika@example.com",
                "bio": "Ingliz tili o'qituvchisi, IELTS murabbiyi. 5 yillik tajriba.",
                "password": "demo1234",
                "role": "user",
            },
            {
                "phone": "+998903456789",
                "name": "Bobur Karimov",
                "email": "bobur@example.com",
                "bio": "Tadbirkor, ko'chmas mulk va IT sohasida faol. Bir necha e'lon egasi.",
                "password": "demo1234",
                "role": "business",
            },
            {
                "phone": "+998904567890",
                "name": "Nilufar Rashidova",
                "email": "nilufar@example.com",
                "bio": "HR mutaxassisi. Ish e'lonlari va resume bilan ishlashni yaxshi ko'raman.",
                "password": "demo1234",
                "role": "user",
            },
            {
                "phone": "+998905678901",
                "name": "Jasur Toshmatov",
                "email": "jasur@example.com",
                "bio": "Haydovchi va xizmat ko'rsatuvchi. Toshkent bo'ylab yetkazib berish.",
                "password": "demo1234",
                "role": "driver",
            },
        ]

        users = []
        for d in users_data:
            u, created = User.objects.get_or_create(
                phone=d["phone"],
                defaults={
                    "name": d["name"],
                    "email": d.get("email"),
                    "bio": d.get("bio", ""),
                    "role": d["role"],
                }
            )
            if created:
                u.set_password(d["password"])
                u.save()
                self.stdout.write(f"  ✅ {u.name} ({u.phone}) [{u.role}]")
            else:
                self.stdout.write(f"  ⏭  Mavjud: {u.name}")
            users.append(u)

        sardor, malika, bobur, nilufar, jasur = users

        # ─── ADMIN (superuser) — /admin/ va boshqaruv paneli uchun ───
        admin, created = User.objects.get_or_create(
            phone="+998900000000",
            defaults={
                "name": "Demo Admin",
                "email": "admin@example.com",
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("admin1234")
            admin.save()
            self.stdout.write("  ✅ Demo Admin (+998900000000) [superuser]")
        else:
            # Mavjud bo'lsa ham admin huquqlarini kafolatlaymiz
            if not (admin.is_staff and admin.is_superuser):
                admin.is_staff = True
                admin.is_superuser = True
                admin.save()
            self.stdout.write("  ⏭  Mavjud: Demo Admin")

        # ─────────────────────────────────────────────────────────────
        # 2. E'LONLAR (Ad) — oddiy e'lonlar
        # ─────────────────────────────────────────────────────────────
        self.stdout.write("\n📋 E'lonlar:")

        ads_data = [
            {
                "user": bobur,
                "category": "uy_joy",
                "title": "Chilonzorda 3 xonali kvartira ijaraga",
                "description": (
                    "Chilonzor 9-kvartalda, 3-qavat, 70 kv.m, yangi ta'mirlangan, "
                    "mebelli, konditsioner bor. Hammasi bor: muzlatgich, kir yuvish mashinasi. "
                    "Kommunal to'lovlar alohida. Oilaga prioritet. Ko'rish uchun qo'ng'iroq qiling."
                ),
                "price": 500000,
                "price_type": "fixed",
                "location": "Toshkent, Chilonzor",
                "contact_phone": "+998903456789",
                "contact_telegram": "@bobur_uy",
                "status": "active",
                "venue_booking_enabled": False,
            },
            {
                "user": sardor,
                "category": "avtomobil",
                "title": "Chevrolet Nexia 3 sotiladi — 2019-yil",
                "description": (
                    "2019-yil, oq rang, 45 000 km yurgan. Mexanik KPP, benzin. "
                    "Barcha hujjatlar joyida, texnik ko'rik o'tilgan. "
                    "Birinchi egasi, jarohatsiz. Narx biroz muzokarali."
                ),
                "price": 13500000,
                "price_type": "negotiable",
                "location": "Toshkent, Yunusobod",
                "contact_phone": "+998901234567",
                "contact_telegram": "@sardor_avto",
                "status": "active",
                "venue_booking_enabled": False,
            },
            {
                "user": malika,
                "category": "xizmat",
                "title": "Ingliz tili darslari — sertifikatlangan o'qituvchi",
                "description": (
                    "IELTS (6.5+ kafolati) va CEFR bo'yicha tayyorlov kurslari. "
                    "Boshlang'ich va o'rta daraja qabul qilinadi. "
                    "Online (Zoom) va offline (Mirzo Ulug'bek, uy). "
                    "Birinchi dars bepul sinov sifatida. Guruh va individual mashg'ulotlar."
                ),
                "price": 80000,
                "price_type": "fixed",
                "location": "Toshkent, Mirzo Ulug'bek",
                "contact_phone": "+998902345678",
                "contact_instagram": "@malika_english",
                "status": "active",
                "venue_booking_enabled": False,
            },
            {
                "user": bobur,
                "category": "uy_joy",
                "title": "Yakkasaroy — zamonaviy ofis xonasi ijaraga",
                "description": (
                    "30 kv.m, 2-qavat, alohida kirish. Tezkor internet, konditsioner, "
                    "24/7 xavfsizlik, avtoturargoh bor. Biznes markaz yaqinida. "
                    "Bron tizimi orqali sana va soat belgilash mumkin."
                ),
                "price": 1200000,
                "price_type": "fixed",
                "location": "Toshkent, Yakkasaroy",
                "contact_phone": "+998903456789",
                "contact_telegram": "@bobur_ofis",
                "status": "active",
                "venue_booking_enabled": True,
                "venue_price_per_day": 1200000,
                "venue_price_per_hour": 150000,
                "venue_capacity": 20,
                "cancellation_policy": "moderate",
            },
            {
                "user": nilufar,
                "category": "xizmat",
                "title": "Konditerlik tort buyurtmasi — Toshkent bo'ylab yetkazib berish",
                "description": (
                    "Tug'ilgan kun, to'y va bayramlar uchun maxsus tortlar. "
                    "Belgiyalik shokolad va tabiiy mahsulotlar. "
                    "Minimal buyurtma: 2 kg. Yetkazib berish bepul (Toshkent ichida)."
                ),
                "price": 120000,
                "price_type": "fixed",
                "location": "Toshkent, Sergeli",
                "contact_phone": "+998904567890",
                "contact_telegram": "@nilufar_tort",
                "status": "active",
                "venue_booking_enabled": False,
            },
            {
                "user": jasur,
                "category": "xizmat",
                "title": "Taksi — Toshkent–Samarqand yo'nalishi (kunlik)",
                "description": (
                    "Qulay va tez. Kvartal-kvartal olib boramiz. "
                    "4 kishi sig'adi, konditsioner, keng salon. "
                    "Kelishuv narxi. Muddatini oldindan bron qiling."
                ),
                "price": 350000,
                "price_type": "negotiable",
                "location": "Toshkent → Samarqand",
                "contact_phone": "+998905678901",
                "contact_telegram": "@jasur_taksi",
                "status": "active",
                "venue_booking_enabled": False,
            },
            {
                "user": sardor,
                "category": "hayvonlar",
                "title": "Skottish fold mushuk bolasi bor — 2 oylik",
                "description": (
                    "Sof qonli, ota-onasi hujjatli. Oq-kulrang rang. "
                    "Barcha emlashlar qilingan, sog'lom. Narx muzokarali. "
                    "Faqat yaxshi qo'llarga beriladi."
                ),
                "price": 2500000,
                "price_type": "negotiable",
                "location": "Toshkent, Yunusobod",
                "contact_phone": "+998901234567",
                "status": "active",
                "venue_booking_enabled": False,
            },
            {
                "user": malika,
                "category": "xizmat",
                "title": "Python dasturlash kursi — noldan professional darajagacha",
                "description": (
                    "3 oylik to'liq kurs. Django, FastAPI, ma'lumotlar bazasi. "
                    "Amaliy loyihalar bilan. Sertifikat beriladi. "
                    "Kichik guruh (max 8 kishi). Dushanba, Chorshanba, Juma — 18:00-20:00."
                ),
                "price": 500000,
                "price_type": "fixed",
                "location": "Toshkent, Mirzo Ulug'bek (online ham mumkin)",
                "contact_telegram": "@malika_courses",
                "status": "active",
                "venue_booking_enabled": False,
            },
        ]

        ads = []
        for d in ads_data:
            existing = Ad.objects.filter(title=d["title"]).first()
            if not existing:
                ad = Ad.objects.create(**d)
                self.stdout.write(f"  ✅ {ad.get_category_display()}: {ad.title[:55]}")
                ads.append(ad)
            else:
                self.stdout.write(f"  ⏭  Mavjud: {existing.title[:55]}")
                ads.append(existing)

        # ─────────────────────────────────────────────────────────────
        # 3. ISH E'LONLARI (JobAd)
        # ─────────────────────────────────────────────────────────────
        self.stdout.write("\n💼 Ish e'lonlari:")

        jobs_data = [
            {
                "user": bobur,
                "title": "Python/Django backend dasturchi",
                "company": "TechStart Uz",
                "job_type": "full_time",
                "salary_min": 3000000,
                "salary_max": 6000000,
                "location": "Toshkent (masofadan ham mumkin)",
                "description": (
                    "E-commerce platformasi uchun backend dasturchi qidirilmoqda. "
                    "Django REST Framework, PostgreSQL, Redis bilishi shart. "
                    "Jamiyat bilan inglizcha muloqot qilish imkoni bor."
                ),
                "requirements": "Django 2+ yil, PostgreSQL, Git, REST API. Ingliz tili — o'rta daraja.",
                "contact_phone": "+998903456789",
                "contact_telegram": "@techstart_hr",
                "deadline": date.today() + timedelta(days=30),
            },
            {
                "user": nilufar,
                "title": "HR Menejeri / Kadrlar bo'limi mutaxassisi",
                "company": "GlobalBiz Toshkent",
                "job_type": "full_time",
                "salary_min": 2500000,
                "salary_max": 4000000,
                "location": "Toshkent, Yunusobod",
                "description": (
                    "Xodimlarni yollash, adaptatsiya qilish, ish muhitini yaxshilash. "
                    "50+ xodimli kompaniya. Istiqbolli ish o'rni, o'sish imkoni bor."
                ),
                "requirements": "HR sohasida 2+ yil tajriba. 1C HR moduli. Rus/ingliz tili.",
                "contact_telegram": "@nilufar_hr_uz",
                "deadline": date.today() + timedelta(days=20),
            },
            {
                "user": sardor,
                "title": "Frontend dasturchi (React/Vue)",
                "company": "Digital Agency Uz",
                "job_type": "remote",
                "salary_min": 2000000,
                "salary_max": 5000000,
                "location": "Masofadan (remote)",
                "description": (
                    "Zamonaviy web ilovalar yaratish. React yoki Vue.js asosida UI. "
                    "Tailwind CSS, responsive dizayn. Scrum/Agile jamoasi."
                ),
                "requirements": "React yoki Vue — 1.5+ yil. JavaScript (ES6+), Git, REST API.",
                "contact_telegram": "@digital_agency_jobs",
                "deadline": date.today() + timedelta(days=45),
            },
            {
                "user": malika,
                "title": "Ingliz tili o'qituvchisi — xususiy maktab",
                "company": "Bright Future School",
                "job_type": "full_time",
                "salary_min": 2000000,
                "salary_max": 3500000,
                "location": "Toshkent, Mirzo Ulug'bek",
                "description": (
                    "6-11 sinf o'quvchilari uchun ingliz tili darslari. "
                    "Zamonaviy uslublar (communicative approach). "
                    "Jadval: Du-Ju, 08:00-16:00. Yoqimli jamoa."
                ),
                "requirements": "IELTS 7.0+ yoki CEFR C1. O'qituvchilik tajribasi 1+ yil.",
                "contact_phone": "+998902345678",
                "deadline": date.today() + timedelta(days=15),
            },
            {
                "user": jasur,
                "title": "Haydovchi (B, C kategoriya) — logistika kompaniyasi",
                "company": "FastDeliver UZ",
                "job_type": "full_time",
                "salary_min": 3000000,
                "salary_max": 4500000,
                "location": "Toshkent va viloyatlar",
                "description": (
                    "Tovarlarni yetkazib berish (Toshkent va regionlar). "
                    "Yangi avtomobil beriladi, yoqilg'i kompaniya hisobidan. "
                    "Soatlik bonus tizimi mavjud."
                ),
                "requirements": "B va C kategoriya, 3+ yil staj. Sog'lom holat. Mas'uliyatli.",
                "contact_phone": "+998905678901",
                "deadline": date.today() + timedelta(days=60),
            },
        ]

        jobs = []
        for d in jobs_data:
            existing = JobAd.objects.filter(title=d["title"]).first()
            if not existing:
                job = JobAd.objects.create(**d)
                self.stdout.write(f"  ✅ {job.title[:55]} | {job.get_job_type_display()}")
                jobs.append(job)
            else:
                self.stdout.write(f"  ⏭  Mavjud: {existing.title[:55]}")
                jobs.append(existing)

        # ─────────────────────────────────────────────────────────────
        # 4. RESUMELAR (ResumeAd)
        # ─────────────────────────────────────────────────────────────
        self.stdout.write("\n📄 Resumelar:")

        resumes_data = [
            {
                "user": sardor,
                "title": "Python/Django Backend Developer",
                "experience": "3_5",
                "salary_min": 4000000,
                "location": "Toshkent (masofadan ham tayyor)",
                "skills": "Python, Django, DRF, PostgreSQL, Redis, Docker, Git, Linux, REST API, Celery",
                "about": (
                    "3 yillik tajribali backend dasturchi. Django/DRF asosida bir necha "
                    "tijorat loyihalarda ishladim. Microservices va monolith arxitekturada "
                    "tajribam bor. CI/CD, Docker bilan ishlashni bilaman. "
                    "Jamoada ishlashni va yangi texnologiyalarni o'rganishni yaxshi ko'raman."
                ),
                "contact_phone": "+998901234567",
                "contact_telegram": "@sardor_dev",
            },
            {
                "user": malika,
                "title": "Ingliz tili o'qituvchisi / IELTS murabbiyi",
                "experience": "3_5",
                "salary_min": 2500000,
                "location": "Toshkent (online va offline)",
                "skills": "IELTS tayyorlov, CEFR, Communicative approach, Cambridge materiallari, Zoom, Google Classroom",
                "about": (
                    "5 yillik o'qituvchilik tajribasi. IELTS 8.0 natijam bor. "
                    "O'quvchilarimning 90%+ maqsad ballni olgan. "
                    "Kattalar va o'smirlar bilan ishlash usullarim farqli. "
                    "Motivatsiya va ruhiy qo'llab-quvvatlashga e'tibor beraman."
                ),
                "contact_telegram": "@malika_english",
            },
            {
                "user": nilufar,
                "title": "HR Manager / Kadrlar bo'limi boshlig'i",
                "experience": "3_5",
                "salary_min": 3500000,
                "location": "Toshkent",
                "skills": "Recruitment, onboarding, 1C HR, Performance review, KPI, Team building, Labour law UZ",
                "about": (
                    "4 yillik HR tajribasi. 100+ xodimli kompaniyada ishlaganman. "
                    "Yollash jarayonini 40% qisqartirish bo'yicha loyiha boshladim. "
                    "O'zbekiston mehnat qonunchiligi bo'yicha bilimim chuqur. "
                    "Kompaniya madaniyatini shakllantirish — kuchli tomonim."
                ),
                "contact_telegram": "@nilufar_hr",
            },
            {
                "user": jasur,
                "title": "Professional haydovchi (B, C, D kategoriya)",
                "experience": "5_plus",
                "salary_min": 3000000,
                "location": "Toshkent va Markaziy Osiyo",
                "skills": "Haydovchilik (B/C/D), navigatsiya, texnik bilim, logistika, VIP xizmat",
                "about": (
                    "8 yillik haydovchilik tajribasi. Hech qanday yo'l-transport hodisasi yo'q. "
                    "Xalqaro marshrutlarda (Qozog'iston, Tojikiston) tajribam bor. "
                    "Avtomobil texnikasini yaxshi bilaman. Punktual va mas'uliyatli."
                ),
                "contact_phone": "+998905678901",
                "contact_telegram": "@jasur_driver",
            },
            {
                "user": bobur,
                "title": "Biznes-tahlilchi / Product Manager",
                "experience": "3_5",
                "salary_min": 5000000,
                "location": "Toshkent",
                "skills": "Product management, Jira, Figma, SQL, Excel, stakeholder management, Agile/Scrum",
                "about": (
                    "IT va ko'chmas mulk sohasida 4 yillik tajriba. "
                    "2 ta muvaffaqiyatli mahsulot ishga tushirishni boshqardim. "
                    "Foydalanuvchi tadqiqoti, prototiplash va analitika — asosiy soham. "
                    "Ingliz tilida erkin muloqot qilaman."
                ),
                "contact_telegram": "@bobur_pm",
            },
        ]

        resumes = []
        for d in resumes_data:
            existing = ResumeAd.objects.filter(title=d["title"], user=d["user"]).first()
            if not existing:
                r = ResumeAd.objects.create(**d)
                self.stdout.write(f"  ✅ {r.title[:55]} — {r.user.name}")
                resumes.append(r)
            else:
                self.stdout.write(f"  ⏭  Mavjud: {existing.title[:55]}")
                resumes.append(existing)

        # ─────────────────────────────────────────────────────────────
        # 5. MAHALLALAR VA CHAT
        # ─────────────────────────────────────────────────────────────
        self.stdout.write("\n🏘  Mahallalar va chat:")

        neighborhoods_data = [
            {"name": "Chilonzor-9 mahallasi",     "description": "Chilonzor tumani, 9-kvartal aholisi uchun"},
            {"name": "Yunusobod-14 mahallasi",    "description": "Yunusobod tumani, 14-kvartal"},
            {"name": "Mirzo Ulug'bek mahallasi",  "description": "Mirzo Ulug'bek tumani, markaziy ko'cha"},
            {"name": "Umumiy muhokama",           "description": "Barcha foydalanuvchilar uchun ochiq chat"},
        ]

        rooms = []
        for nd in neighborhoods_data:
            n, created = Neighborhood.objects.get_or_create(
                name=nd["name"], defaults={"description": nd["description"]}
            )
            room, _ = ChatRoom.objects.get_or_create(neighborhood=n)
            rooms.append(room)
            if created:
                self.stdout.write(f"  ✅ {n.name}")
            else:
                self.stdout.write(f"  ⏭  Mavjud: {n.name}")

        r_chilonzor, r_yunusobod, r_mirzo, r_umumiy = rooms

        chat_messages_data = [
            # Chilonzor
            (r_chilonzor, sardor,  "Salom qo'shnilar! Ertaga kechqurun yig'ilish bo'ladimi?"),
            (r_chilonzor, malika,  "Ha, soat 18:00 da bo'ladi, lift yaqinida."),
            (r_chilonzor, bobur,   "Mavzu nima? Ko'cha yoritgichlari haqidami?"),
            (r_chilonzor, sardor,  "Ha, va yangi bog'cha qurilishi ham muhokamada."),
            (r_chilonzor, nilufar, "Men ham boraman. Bolalar uchun maydon so'rash kerak."),
            (r_chilonzor, jasur,   "Yig'ilishga ulgura olmayman, natijasini yozib qo'ying."),
            # Yunusobod
            (r_yunusobod, bobur,   "Yunusobod mahallasiga xush kelibsiz!"),
            (r_yunusobod, malika,  "Bizning mahallada yangi dorixona ochildi, juda qulay."),
            (r_yunusobod, sardor,  "Qayerda? Manzilini yuboring."),
            (r_yunusobod, malika,  "14-kvartal, 3-uy yaqinida. Ertalab 8 dan kechgacha."),
            (r_yunusobod, nilufar, "Rahmat! Uzoq vaqt dorixona qidirardim."),
            # Mirzo Ulug'bek
            (r_mirzo, nilufar, "Mirzo Ulug'bek mahallasi - sakin va yashil joy!"),
            (r_mirzo, bobur,   "To'g'ri, lekin avtobuslar kam. Ariza beraylik birgalikda."),
            (r_mirzo, nilufar, "Yaxshi fikr. Imzo to'playlik, 50 ta bo'lsa yetarli."),
            (r_mirzo, jasur,   "Men ham qo'shilaman. Shu masala ko'p yildan beri hal bo'lmaydi."),
            # Umumiy
            (r_umumiy, sardor,  "Bu platforma juda qulay ekan! Hamma narsani topsa bo'ladi."),
            (r_umumiy, malika,  "Ha, ayniqsa ish e'lonlari bo'limi foydali."),
            (r_umumiy, bobur,   "Mahallalar chat tizimi ham ajoyib g'oya."),
            (r_umumiy, jasur,   "Bron tizimi ham bor ekan, ishlatib ko'raman."),
            (r_umumiy, nilufar, "Kommunal to'lovlarni kuzatish funksiyasi foydali!"),
        ]

        added_msgs = 0
        for room, user, text in chat_messages_data:
            if not ChatMessage.objects.filter(room=room, user=user, text=text).exists():
                ChatMessage.objects.create(room=room, user=user, text=text)
                added_msgs += 1
        self.stdout.write(f"  ✅ {added_msgs} ta yangi xabar qo'shildi")

        # ─────────────────────────────────────────────────────────────
        # 6. BRONLAR (Booking) — venue bron + to'lov holatlari
        # ─────────────────────────────────────────────────────────────
        self.stdout.write("\n📅 Bronlar:")

        venue_ad = next((a for a in ads if a.venue_booking_enabled), None)

        bookings_data = []
        if venue_ad:
            today = date.today()
            bookings_data = [
                {
                    "ad": venue_ad,
                    "buyer": malika,
                    "owner": venue_ad.user,
                    "message": "Yakshanba kuniga seminar o'tkazish uchun bron qilyapman. 15 kishilik guruh.",
                    "guests": 15,
                    "start_date": today + timedelta(days=5),
                    "end_date":   today + timedelta(days=6),
                    "total_amount": venue_ad.venue_price_per_day,
                    "platform_fee": int((venue_ad.venue_price_per_day or 0) * 0.10),
                    "owner_amount": int((venue_ad.venue_price_per_day or 0) * 0.90),
                    "payment_status": "held",
                    "status": "pending",
                },
                {
                    "ad": venue_ad,
                    "buyer": sardor,
                    "owner": venue_ad.user,
                    "message": "2 kunlik treningga joy kerak. Proyektor va doskangiz bormi?",
                    "guests": 10,
                    "start_date": today + timedelta(days=10),
                    "end_date":   today + timedelta(days=12),
                    "total_amount": (venue_ad.venue_price_per_day or 0) * 2,
                    "platform_fee": int((venue_ad.venue_price_per_day or 0) * 2 * 0.10),
                    "owner_amount": int((venue_ad.venue_price_per_day or 0) * 2 * 0.90),
                    "payment_status": "held",
                    "status": "confirmed",
                },
                {
                    "ad": venue_ad,
                    "buyer": nilufar,
                    "owner": venue_ad.user,
                    "message": "Intervyu o'tkazish uchun 3 soat kerak.",
                    "guests": 5,
                    "start_date": today - timedelta(days=5),
                    "end_date":   today - timedelta(days=4),
                    "total_amount": venue_ad.venue_price_per_day,
                    "platform_fee": int((venue_ad.venue_price_per_day or 0) * 0.10),
                    "owner_amount": int((venue_ad.venue_price_per_day or 0) * 0.90),
                    "payment_status": "released",
                    "status": "completed",
                },
                {
                    "ad": venue_ad,
                    "buyer": jasur,
                    "owner": venue_ad.user,
                    "message": "Uchrashuv uchun bron qilmoqchi edim.",
                    "guests": 3,
                    "start_date": today + timedelta(days=2),
                    "end_date":   today + timedelta(days=3),
                    "total_amount": venue_ad.venue_price_per_day,
                    "platform_fee": int((venue_ad.venue_price_per_day or 0) * 0.10),
                    "owner_amount": int((venue_ad.venue_price_per_day or 0) * 0.90),
                    "refund_amount": venue_ad.venue_price_per_day,
                    "payment_status": "refunded",
                    "status": "cancelled",
                    "cancelled_by": "buyer",
                },
            ]

        for bd in bookings_data:
            exists = Booking.objects.filter(ad=bd["ad"], buyer=bd["buyer"]).exists()
            if not exists:
                Booking.objects.create(**bd)
                self.stdout.write(
                    f"  ✅ {bd['buyer'].name} → {bd['ad'].title[:35]} "
                    f"[{bd['status']}|{bd['payment_status']}]"
                )
            else:
                self.stdout.write(f"  ⏭  Mavjud bron: {bd['buyer'].name}")

        # ─────────────────────────────────────────────────────────────
        # 7. KOMMUNAL TO'LOVLAR (UtilityPayment)
        # ─────────────────────────────────────────────────────────────
        self.stdout.write("\n💡 Kommunal to'lovlar:")

        from datetime import date as d_
        today_ = d_.today()
        this_month  = today_.strftime('%Y-%m')
        last_month  = (today_.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        prev2_month = (today_.replace(day=1) - timedelta(days=32)).strftime('%Y-%m')

        utility_data = [
            # Sardor — 3 oylik to'lovlar
            {
                "user": sardor, "service": "elektr", "amount": 85000,
                "period": this_month, "status": "tolangan",
                "note": "Iyun oyi elektr", "paid_at": today_,
            },
            {
                "user": sardor, "service": "suv", "amount": 32000,
                "period": this_month, "status": "tolangan",
                "note": "", "paid_at": today_,
            },
            {
                "user": sardor, "service": "gaz", "amount": 48000,
                "period": last_month, "status": "tolangan",
                "note": "May oyi gaz", "paid_at": today_ - timedelta(days=10),
            },
            {
                "user": sardor, "service": "internet", "amount": 65000,
                "period": this_month, "status": "kutilmoqda",
                "note": "Ucell Fiber 50 Mbps", "paid_at": today_ + timedelta(days=5),
            },
            # Malika
            {
                "user": malika, "service": "elektr", "amount": 62000,
                "period": this_month, "status": "tolangan",
                "note": "", "paid_at": today_ - timedelta(days=2),
            },
            {
                "user": malika, "service": "internet", "amount": 75000,
                "period": this_month, "status": "tolangan",
                "note": "Beeline Home", "paid_at": today_ - timedelta(days=1),
            },
            {
                "user": malika, "service": "uy_fondi", "amount": 120000,
                "period": last_month, "status": "muddati_otgan",
                "note": "May oyi uy-joy fondi — kech to'landi", "paid_at": today_ - timedelta(days=20),
            },
            # Bobur
            {
                "user": bobur, "service": "elektr", "amount": 210000,
                "period": this_month, "status": "tolangan",
                "note": "Ofis elektr", "paid_at": today_,
            },
            {
                "user": bobur, "service": "gaz", "amount": 95000,
                "period": this_month, "status": "tolangan",
                "note": "", "paid_at": today_,
            },
            {
                "user": bobur, "service": "suv", "amount": 55000,
                "period": prev2_month, "status": "tolangan",
                "note": "Aprel oyi suv", "paid_at": today_ - timedelta(days=45),
            },
            {
                "user": bobur, "service": "internet", "amount": 150000,
                "period": this_month, "status": "kutilmoqda",
                "note": "Optima Telecom biznes tarif", "paid_at": today_ + timedelta(days=3),
            },
            # Nilufar
            {
                "user": nilufar, "service": "elektr", "amount": 45000,
                "period": this_month, "status": "tolangan",
                "note": "", "paid_at": today_ - timedelta(days=3),
            },
            {
                "user": nilufar, "service": "telefon", "amount": 35000,
                "period": this_month, "status": "tolangan",
                "note": "Uzmobile", "paid_at": today_ - timedelta(days=1),
            },
        ]

        added_util = 0
        for d in utility_data:
            exists = UtilityPayment.objects.filter(
                user=d["user"], service=d["service"], period=d["period"]
            ).exists()
            if not exists:
                UtilityPayment.objects.create(**d)
                added_util += 1

        self.stdout.write(f"  ✅ {added_util} ta yangi to'lov qo'shildi")

        # ─────────────────────────────────────────────────────────────
        # YAKUNIY HISOBOT
        # ─────────────────────────────────────────────────────────────
        from main.models import User as U, Ad as A, JobAd as J, ResumeAd as R
        from main.models import Neighborhood as N, ChatMessage as CM
        from main.models import Booking as B, UtilityPayment as UP

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ Demo ma'lumotlar muvaffaqiyatli yuklandi!"))
        self.stdout.write("=" * 60)
        self.stdout.write("")
        self.stdout.write("📊 STATISTIKA:")
        self.stdout.write(f"   👤 Foydalanuvchilar:      {U.objects.count()} ta")
        self.stdout.write(f"   📋 E'lonlar:              {A.objects.count()} ta")
        self.stdout.write(f"   💼 Ish e'lonlari:         {J.objects.count()} ta")
        self.stdout.write(f"   📄 Resumelar:             {R.objects.count()} ta")
        self.stdout.write(f"   🏘  Mahallalar:           {N.objects.count()} ta")
        self.stdout.write(f"   💬 Chat xabarlari:        {CM.objects.count()} ta")
        self.stdout.write(f"   📅 Bronlar:               {B.objects.count()} ta")
        self.stdout.write(f"   💡 Kommunal to'lovlar:    {UP.objects.count()} ta")
        self.stdout.write("")
        self.stdout.write("🔑 DEMO HISOBLAR (parol: demo1234):")
        self.stdout.write("   +998900000000  →  Demo Admin         [superuser, parol: admin1234]")
        self.stdout.write("   +998901234567  →  Sardor Aliyev      [user]")
        self.stdout.write("   +998902345678  →  Malika Yusupova    [user, o'qituvchi]")
        self.stdout.write("   +998903456789  →  Bobur Karimov      [business, e'lon egasi]")
        self.stdout.write("   +998904567890  →  Nilufar Rashidova  [user, HR]")
        self.stdout.write("   +998905678901  →  Jasur Toshmatov    [driver]")
        self.stdout.write("")
        self.stdout.write("🌐 ISHGA TUSHIRISH:")
        self.stdout.write("   python manage.py runserver")
        self.stdout.write("   http://127.0.0.1:8000/")
        self.stdout.write("")
        self.stdout.write("🗑  TOZALASH VA QAYTA YUKLASH:")
        self.stdout.write("   python manage.py demo_data --clear")
        self.stdout.write("")
