from django.core.management.base import BaseCommand
from places.models import Place

# (name, category, address, lat, lng, phone, hours)
PLACES = [
    ("Diyor Mebel", "furniture", "Markaziy ko'cha 3", 40.1162, 64.5050, "+998 90 100 10 01", "09:00–19:00"),
    ("Yoshlar istirohat bog'i", "tourist", "Markaziy maydon", 40.1140, 64.5012, "", "06:00–23:00"),
    ("Elektro Plus", "electronics", "Markaz", 40.1170, 64.5031, "+998 90 200 20 01", "09:00–20:00"),
    ("MediaPark elektronika", "electronics", "Yangi bozor", 40.1131, 64.5065, "+998 90 200 20 03", "10:00–21:00"),
    ("Shofirkon qal'asi", "tourist", "Tarixiy markaz", 40.1185, 64.5040, "", "24/7"),
    ("Qadimiy masjid", "tourist", "Eski shahar", 40.1149, 64.4998, "", "06:00–21:00"),
    ("Tuman hokimligi", "government", "Mustaqillik maydoni 1", 40.1158, 64.5044, "+998 65 770 00 00", "09:00–18:00"),
    ("Davlat xizmatlari markazi", "government", "Markaz", 40.1166, 64.5022, "+998 65 770 11 11", "09:00–18:00"),
    ("Soliq inspeksiyasi", "organization", "Markaziy ko'cha 20", 40.1144, 64.5057, "+998 65 771 22 33", "09:00–18:00"),
    ("Pochta bo'limi №1", "post", "Markaz", 40.1153, 64.5036, "+998 65 772 00 11", "08:00–18:00"),
    ("Milliy bank", "bank", "Mustaqillik 5", 40.1160, 64.5060, "+998 65 773 00 22", "09:00–17:00"),
    ("Kapitalbank", "bank", "Bozor yoni", 40.1138, 64.5028, "+998 65 773 44 55", "09:00–18:00"),
    ("Dorixona Shifo", "pharmacy", "Markaz", 40.1156, 64.5048, "+998 90 300 30 01", "08:00–22:00"),
    ("24/7 Dorixona", "pharmacy", "Yoshlik 2", 40.1172, 64.5015, "+998 90 300 30 02", "24/7"),
    ("Tuman markaziy shifoxonasi", "hospital", "Tibbiyot ko'chasi 1", 40.1190, 64.5010, "+998 65 774 00 00", "24/7"),
    ("Oilaviy poliklinika", "hospital", "Markaz", 40.1128, 64.5042, "+998 65 774 11 11", "08:00–20:00"),
    ("Grand Hotel Shofirkon", "hotel", "Markaziy ko'cha 30", 40.1167, 64.5055, "+998 90 400 40 09", "24/7"),
    ("Diyor To'yxona", "wedding", "Bog' ko'chasi 1", 40.1135, 64.5005, "+998 90 700 10 01", "10:00–23:00"),
    ("Milliy Osh Markazi", "restaurant", "Markaz", 40.1151, 64.5039, "+998 90 700 20 02", "09:00–23:00"),
    ("Cafe Shirin", "restaurant", "Markaziy maydon", 40.1163, 64.5033, "+998 90 700 50 05", "08:00–23:00"),
    ("Shofirkon Market", "delivery_store", "Markaziy ko'cha 1", 40.1155, 64.5046, "+998 90 111 00 11", "08:00–22:00"),
]


class Command(BaseCommand):
    help = "Xarita uchun demo joylar (barcha toifalar bo'yicha)."

    def handle(self, *args, **opts):
        n = 0
        for name, cat, addr, lat, lng, phone, hours in PLACES:
            Place.objects.update_or_create(
                name=name,
                defaults={
                    'category': cat, 'address': addr, 'latitude': lat, 'longitude': lng,
                    'phone': phone, 'working_hours': hours, 'is_active': True,
                    'description': f"{name} — Shofirkon shahridagi {dict(Place._meta.get_field('category').choices).get(cat,'')}.",
                },
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(f"✅ {n} ta joy xaritaga qo'shildi! Sahifa: /map/"))
