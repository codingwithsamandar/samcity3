╔══════════════════════════════════════════════════════════╗
║           SDEV — TO'LIQ LOYIHA (MERGED)                 ║
╠══════════════════════════════════════════════════════════╣
║  ✅ E'lonlar tizimi                                      ║
║  ✅ Mahalla chat (WebSocket real-time)                   ║
║  ✅ Bron qilish tizimi                                   ║
╚══════════════════════════════════════════════════════════╝

─── BIRINCHI MARTA ISHGA TUSHIRISH ──────────────────────

1. Virtual environment (ixtiyoriy):
   python -m venv venv
   venv\Scripts\activate          (Windows)
   source venv/bin/activate       (Mac/Linux)

2. Paketlarni o'rnatish:
   pip install django channels daphne pillow

3. Bazani yaratish:
   python manage.py migrate

4. Demo ma'lumotlarni yuklash:
   python manage.py demo_data

5. Serverni ishga tushirish:
   python manage.py runserver

─── DEMO HISOBLAR (parol: demo1234) ─────────────────────

   +998901234567  —  Sardor Aliyev
   +998902345678  —  Malika Yusupova
   +998903456789  —  Bobur Karimov  (biznes, e'lon egasi)
   +998904567890  —  Nilufar Rashidova

─── ADMIN PANEL ─────────────────────────────────────────

   python manage.py createsuperuser
   http://127.0.0.1:8000/admin/

─── MUHIM SAHIFALAR ─────────────────────────────────────

   /                        — Bosh sahifa (e'lonlar)
   /profile/                — Profil
   /ads/create/             — E'lon qo'shish
   /neighborhood-chat/      — Mahalla chatlari
   /bookings/               — Mening bronlarim
   /bookings/received/      — Menga kelgan bronlar

