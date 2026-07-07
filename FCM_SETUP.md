# FCM push-bildirishnomalarni ulash (backend tayyor)

Backend to'liq tayyor: token saqlash (`DeviceToken`), API endpoint va yuborish
moduli (`notifications/push.py`) mavjud. Firebase sozlanmaguncha push **jimgina
o'chiq** — hech narsa buzilmaydi, WebSocket bildirishnomalar ishlayveradi.

## 1. Backend (5 daqiqa)

1. [Firebase Console](https://console.firebase.google.com) da loyiha yarating.
2. Project settings → Service accounts → **Generate new private key** → JSON yuklab oling.
3. JSON faylni serverga qo'ying (masalan `/etc/samcity/firebase.json`) va `.env` ga yozing:
   ```
   FIREBASE_CREDENTIALS_FILE=/etc/samcity/firebase.json
   ```
4. `pip install firebase-admin` (requirements.txt da bor — `pip install -r requirements.txt` yetarli).
5. Migratsiya: `python manage.py migrate notifications`

Shu bilan `notify()` chaqirilgan har bir joy (buyurtma holati, bron, chat, ...)
avtomatik FCM push ham yuboradi. Yaroqsiz tokenlar o'z-o'zidan o'chiriladi.

## 2. API (mobil ilova uchun tayyor)

| Metod | URL | Tana | Izoh |
|---|---|---|---|
| POST | `/api/notifications/device/` | `{"token": "...", "platform": "android"}` | Login'dan keyin |
| DELETE | `/api/notifications/device/` | `{"token": "..."}` | Logout'da |

Ikkalasi ham JWT talab qiladi (`Authorization: Bearer <access>`).

## 3. Mobil (Flutter) — qadamlar

1. `flutterfire configure` (FlutterFire CLI) — `google-services.json` (Android)
   va `GoogleService-Info.plist` (iOS) avtomatik qo'shiladi.
2. `pubspec.yaml` ga:
   ```yaml
   firebase_core: ^3.6.0
   firebase_messaging: ^15.1.3
   ```
3. `main.dart` da init + token yuborish:
   ```dart
   await Firebase.initializeApp();
   final token = await FirebaseMessaging.instance.getToken();
   if (token != null) {
     await api.post('/notifications/device/',
         data: {'token': token, 'platform': Platform.isIOS ? 'ios' : 'android'});
   }
   FirebaseMessaging.instance.onTokenRefresh.listen((t) =>
       api.post('/notifications/device/', data: {'token': t}));
   ```
4. Logout'da: `DELETE /notifications/device/` + `FirebaseMessaging.instance.deleteToken()`.
5. Android 13+ uchun runtime ruxsat: `FirebaseMessaging.instance.requestPermission()`.

> Eslatma: `google-services.json` qo'shilmaguncha `firebase_*` paketlarini
> pubspec'ga qo'shmang — build buziladi. Shuning uchun mobil kod bu repoda
> hali qo'shilmagan; backend esa to'liq tayyor.

## 4. Tekshirish

```bash
python manage.py shell -c "
from main.models import User
from notifications.models import notify
u = User.objects.first()
notify(u, 'Test push 🎉')   # DeviceToken bo'lsa va Firebase sozlansa — telefonga boradi
"
```
