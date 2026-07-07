"""FCM (Firebase Cloud Messaging) push yuborish — backend-tayyor, ixtiyoriy.

Ishlash sharti (ikkalasi ham bo'lsa yoqiladi, aks holda jimgina o'chiq):
  1. `pip install firebase-admin` (requirements.txt da ixtiyoriy blokda)
  2. `.env` da `FIREBASE_CREDENTIALS_FILE=/path/to/serviceAccountKey.json`

Hech biri bo'lmasa — hech narsa buzilmaydi: `send_push()` shunchaki False
qaytaradi. WebSocket yetkazish (models._push_realtime) mustaqil ishlayveradi.

Mobil tomonni ulash bo'yicha to'liq yo'riqnoma: FCM_SETUP.md
"""
import logging
import os
import threading

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_initialized = False
_enabled = None  # None = hali aniqlanmagan


def _init():
    """firebase_admin ni bir marta ishga tushiradi. Muvaffaqiyat: True."""
    global _initialized, _enabled
    if _enabled is not None:
        return _enabled
    with _lock:
        if _enabled is not None:
            return _enabled
        cred_path = os.environ.get('FIREBASE_CREDENTIALS_FILE', '').strip()
        if not cred_path or not os.path.exists(cred_path):
            _enabled = False
            return False
        try:
            import firebase_admin
            from firebase_admin import credentials
            if not firebase_admin._apps:
                firebase_admin.initialize_app(credentials.Certificate(cred_path))
            _initialized = True
            _enabled = True
            logger.info('FCM push yoqildi (%s)', cred_path)
        except ImportError:
            logger.warning(
                'FIREBASE_CREDENTIALS_FILE berilgan, lekin firebase-admin '
                "o'rnatilmagan — `pip install firebase-admin`. Push o'chiq."
            )
            _enabled = False
        except Exception:
            logger.exception('FCM ishga tushmadi — push o\'chiq.')
            _enabled = False
        return _enabled


def is_enabled():
    return _init()


def send_push(user, title, body, data=None):
    """Foydalanuvchining barcha faol qurilmalariga push yuboradi (best-effort).

    Yaroqsiz (o'chirilgan ilova) tokenlar avtomatik deaktivatsiya qilinadi.
    Qaytaradi: yuborilgan xabarlar soni (int) yoki False (push o'chiq).
    """
    if user is None or not _init():
        return False

    from .models import DeviceToken
    tokens = list(
        DeviceToken.objects.filter(user=user, is_active=True)
        .values_list('token', flat=True)
    )
    if not tokens:
        return 0

    try:
        from firebase_admin import messaging
    except ImportError:  # pragma: no cover — _init() bunga yo'l qo'ymaydi
        return False

    payload = {str(k): str(v) for k, v in (data or {}).items()}
    sent, dead = 0, []
    for token in tokens:
        msg = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=payload,
            android=messaging.AndroidConfig(priority='high'),
        )
        try:
            messaging.send(msg)
            sent += 1
        except messaging.UnregisteredError:
            dead.append(token)
        except Exception:
            logger.warning('FCM yuborishda xato (token yashirin).', exc_info=True)

    if dead:
        DeviceToken.objects.filter(token__in=dead).update(is_active=False)
    return sent
