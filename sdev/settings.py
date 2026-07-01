from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path):
    """BASE_DIR/.env faylini o'qib os.environ ga yuklaydi (qo'shimcha paketsiz).

    Haqiqiy muhit o'zgaruvchilari ustun (setdefault) — docker-compose/CI
    bergan qiymatlarni .env bekor qilmaydi. KEY=VALUE, '#' izohlar e'tiborsiz.
    """
    try:
        if not path.exists():
            return
        for raw in path.read_text(encoding='utf-8').splitlines():
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, val = line.partition('=')
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, val)
    except OSError:
        pass


_load_dotenv(BASE_DIR / '.env')


def env_bool(key, default=False):
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ('1', 'true', 'yes', 'on')

# ─── XAVFSIZLIK ──────────────────────────────────────────────────────────────
# DEBUG: muhit o'zgaruvchisidan boshqariladi (default — development uchun True)
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes', 'on')

# SECRET_KEY: production uchun DJANGO_SECRET_KEY SHART.
# DEBUG=False bo'lsa va kalit berilmagan bo'lsa — ishga tushmaydi (xavfsizlik).
_DEV_SECRET = 'django-insecure-do^_sgnv(rq*5z8#j@*p!$g0u$(^gz8^2x7jraic#yek$%avbe'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '' if not DEBUG else _DEV_SECRET)
if not SECRET_KEY:
    raise RuntimeError(
        "DJANGO_SECRET_KEY muhit o'zgaruvchisi o'rnatilmagan. "
        "Production uchun uni o'rnating (DEBUG=False)."
    )

# ALLOWED_HOSTS: vergul bilan ajratilgan ro'yxat. DEBUG da hammasi ruxsat.
_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '').strip()
if _hosts:
    ALLOWED_HOSTS = [h.strip() for h in _hosts.split(',') if h.strip()]
elif DEBUG:
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '*']
else:
    ALLOWED_HOSTS = []

# Session: "Meni eslab qol" 30 kun ishlaydi
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 kun
SESSION_SAVE_EVERY_REQUEST = False

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'channels',
    'django.contrib.staticfiles',
    # ── Mobile REST API (Flutter ilova) ──
    'rest_framework',
    'corsheaders',
    'drf_spectacular',
    'django_filters',
    # ── Loyiha app'lari ──
    'main',
    'delivery',
    'taxi',
    'payments',
    'booking',
    'notifications',
    'places',
    'api',
    'sms',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise: statik fayllarni nginx'siz beradi (Render/Koyeb bitta konteyner).
    # SecurityMiddleware'dan keyin, boshqalardan oldin turishi SHART.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS — mobil/web klient uchun (eng yuqorida)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sdev.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'sdev.wsgi.application'
ASGI_APPLICATION = 'sdev.asgi.application'

# ─── DATABASE ────────────────────────────────────────────────────────────────
# Default: SQLite (development). Set POSTGRES_DB to switch to PostgreSQL
# (production). No psycopg2 needed unless Postgres is actually selected.
if os.environ.get('POSTGRES_DB'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ['POSTGRES_DB'],
            'USER': os.environ.get('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
            'HOST': os.environ.get('POSTGRES_HOST', '127.0.0.1'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ─── CHANNEL LAYER ───────────────────────────────────────────────────────────
# Default: in-memory (development). Set REDIS_URL to use Redis (production),
# which is required for real-time features across multiple workers/processes.
REDIS_URL = os.environ.get('REDIS_URL', '')
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'},
    }

# ─── CACHE ───────────────────────────────────────────────────────────────────
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'samcity-cache',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

# Leading slash is required so {% static %} resolves correctly on every URL path.
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # collectstatic uchun

# WhiteNoise: statik fayllarni siqib (gzip/brotli) va xeshli nom bilan beradi.
# nginx bo'lmagan deploy'da (Render/Koyeb) DEBUG=False'da statik shu orqali ishlaydi.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── MEDIA STORAGE (production — Render disk ephemeral) ─────────────────────
# Cloudinary (tavsiya) yoki AWS S3. Env o'rnatilmasa — local FileSystemStorage.
_cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
_cloud_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
_cloud_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()
_s3_bucket = os.environ.get('AWS_STORAGE_BUCKET_NAME', '').strip()

if _cloud_name and _cloud_key and _cloud_secret:
    _static_idx = INSTALLED_APPS.index('django.contrib.staticfiles')
    INSTALLED_APPS.insert(_static_idx, 'cloudinary_storage')
    INSTALLED_APPS.append('cloudinary')
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': _cloud_name,
        'API_KEY': _cloud_key,
        'API_SECRET': _cloud_secret,
    }
    STORAGES['default'] = {'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage'}
    MEDIA_URL = f'https://res.cloudinary.com/{_cloud_name}/'
elif _s3_bucket:
    INSTALLED_APPS += ['storages']
    AWS_STORAGE_BUCKET_NAME = _s3_bucket
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', '')
    AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN', '')
    AWS_DEFAULT_ACL = 'public-read'
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    STORAGES['default'] = {'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage'}
    # Supabase public URL format
    _s3_endpoint = AWS_S3_ENDPOINT_URL
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
    elif 'supabase.co' in _s3_endpoint:
        # Supabase public object URL: .../object/public/<bucket>/
        _supabase_host = _s3_endpoint.replace('/storage/v1/s3', '')
        MEDIA_URL = f'{_supabase_host}/storage/v1/object/public/{_s3_bucket}/'
    elif _s3_endpoint:
        MEDIA_URL = f'{_s3_endpoint}/{_s3_bucket}/'
    else:
        MEDIA_URL = f'https://{_s3_bucket}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/'
LOGIN_REDIRECT_URL = 'profile'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/login/'
AUTH_USER_MODEL = 'main.User'

# Production uchun: CSRF_TRUSTED_ORIGINS=https://yourdomain.com qilib o'rnatish SHART
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'http://127.0.0.1:8000,http://localhost:8000'
).split(',')

# ─── SECURITY (production — applied only when DEBUG is False) ─────────────────
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_HTTPONLY = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'same-origin'

# ─── LOGGING ─────────────────────────────────────────────────────────────────
LOG_DIR = BASE_DIR / 'logs'
_log_to_file = True
try:
    LOG_DIR.mkdir(exist_ok=True)
except OSError:
    _log_to_file = False  # read-only FS — fall back to console only

_log_handlers = {
    'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
}
if _log_to_file:
    _log_handlers['file'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': str(LOG_DIR / 'samcity.log'),
        'maxBytes': 5 * 1024 * 1024,
        'backupCount': 3,
        'formatter': 'verbose',
    }
_handler_names = list(_log_handlers.keys())

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {name} {message}', 'style': '{'},
        'simple': {'format': '{levelname} {message}', 'style': '{'},
    },
    'handlers': _log_handlers,
    'root': {
        'handlers': _handler_names,
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': _handler_names,
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': _handler_names,
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# Default upload size cap (defense-in-depth for file sharing endpoints)
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get('DATA_UPLOAD_MAX_MEMORY_SIZE', str(10 * 1024 * 1024)))

# ─── REST API (Flutter mobil ilova) ──────────────────────────────────────────
from datetime import timedelta  # noqa: E402

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',  # brauzerda DRF panel uchun
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/min',
        'user': '300/min',
        # Maxsus (scoped) limitlar — SMS-bombing va brute-force himoyasi.
        # Bir telefon raqamiga ko'p OTP yuborilishining oldini oladi.
        'otp_send': '5/min',
        'otp_verify': '10/min',
        'login': '10/min',
        'checkout': '20/min',
        'payment_init': '30/min',
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.environ.get('JWT_ACCESS_MINUTES', '60'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.environ.get('JWT_REFRESH_DAYS', '30'))),
    'ROTATE_REFRESH_TOKENS': True,
    'UPDATE_LAST_LOGIN': True,
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'SamCity API',
    'DESCRIPTION': 'SamCity super-app uchun mobil REST API (Flutter ilova).',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# CORS: mobil ilovada origin yo'q, lekin web-klient/test uchun sozlanadi.
# Productionda CORS_ALLOWED_ORIGINS ni aniq domenlar bilan to'ldiring.
_cors = os.environ.get('CORS_ALLOWED_ORIGINS', '').strip()
if _cors:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors.split(',') if o.strip()]
else:
    CORS_ALLOW_ALL_ORIGINS = DEBUG  # faqat development'da hammaga ruxsat

# ─── TO'LOV SHLYUZI (Payme / Click) ──────────────────────────────────────────
# Productionda bu qiymatlar Payme/Click kabinetidan olinadi va env orqali
# o'rnatiladi. Bo'sh bo'lsa — webhook'lar autentifikatsiyadan o'tmaydi (xavfsiz).
PAYME_MERCHANT_ID = os.environ.get('PAYME_MERCHANT_ID', '')
PAYME_MERCHANT_KEY = os.environ.get('PAYME_MERCHANT_KEY', '')
PAYME_CHECKOUT_URL = os.environ.get('PAYME_CHECKOUT_URL', 'https://checkout.paycom.uz')

CLICK_SERVICE_ID = os.environ.get('CLICK_SERVICE_ID', '')
CLICK_MERCHANT_ID = os.environ.get('CLICK_MERCHANT_ID', '')
CLICK_SECRET_KEY = os.environ.get('CLICK_SECRET_KEY', '')
CLICK_MERCHANT_USER_ID = os.environ.get('CLICK_MERCHANT_USER_ID', '')
CLICK_CHECKOUT_URL = os.environ.get('CLICK_CHECKOUT_URL', 'https://my.click.uz/services/pay')

# ─── SMS SHLYUZI ─────────────────────────────────────────────────────────────
# SMS_BACKEND: 'eskiz' | 'playmobile' | 'console' (default).
# DEBUG=True bo'lsa ham 'console' qulay (haqiqiy SMS yubormaydi).
SMS_BACKEND = os.environ.get('SMS_BACKEND', 'console' if DEBUG else 'eskiz')
# Testlarda hech qachon haqiqiy SMS yubormaymiz (tarmoq timeout'i + flakiness):
import sys as _sys
if 'test' in _sys.argv:
    SMS_BACKEND = 'console'
SMS_ESKIZ_EMAIL = os.environ.get('SMS_ESKIZ_EMAIL', '')
SMS_ESKIZ_PASSWORD = os.environ.get('SMS_ESKIZ_PASSWORD', '')
SMS_ESKIZ_FROM = os.environ.get('SMS_ESKIZ_FROM', '4546')
SMS_PLAYMOBILE_LOGIN = os.environ.get('SMS_PLAYMOBILE_LOGIN', '')
SMS_PLAYMOBILE_PASSWORD = os.environ.get('SMS_PLAYMOBILE_PASSWORD', '')
SMS_PLAYMOBILE_FROM = os.environ.get('SMS_PLAYMOBILE_FROM', '3700')

# ─── MONITORING: Sentry (ixtiyoriy — faqat SENTRY_DSN o'rnatilganda) ──────────
SENTRY_DSN = os.environ.get('SENTRY_DSN', '').strip()
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=float(os.environ.get('SENTRY_TRACES_RATE', '0.0')),
            send_default_pii=False,
            environment=('production' if not DEBUG else 'development'),
        )
    except Exception:
        # Sentry o'rnatilmagan bo'lsa — jim o'tkazib yuboramiz
        pass
