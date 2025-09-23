from pathlib import Path
import os
import environ

# =========================
# Paths & .env
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# =========================
# Seguridad (dev)
# =========================
SECRET_KEY = env("SECRET_KEY", default="PrebelAyT")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]", "0.0.0.0"])

if DEBUG:
    import socket
    try:
        hostname = socket.gethostname()
        local_ips = list(set(socket.gethostbyname_ex(hostname)[2]))
        # Evita duplicados y agrega hostname/ip locales automáticamente en dev
        ALLOWED_HOSTS = list(set(ALLOWED_HOSTS + [hostname] + local_ips))
    except Exception:
        # Si falla la resolución, seguimos con lo definido en .env
        pass

gcred = env("GOOGLE_APPLICATION_CREDENTIALS", default="")
if gcred and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcred

# =========================
# Apps
# =========================
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "drf_spectacular",
    # Local
    "app",
]

# =========================
# Middleware
# =========================
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",      # CORS primero
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =========================
# CORS / CSRF (frontend local)
# =========================
from corsheaders.defaults import default_headers

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# Orígenes del front (Next/Vite)
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://172.24.66.25:3000",
        "http://172.24.66.23:3000",
        "http://172.24.66.23",
    ],
)

# Permite IP local (LAN) tipo 192.168.x.x:3000/5173
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://((192\.168|10|172\.(1[6-9]|2\d|3[0-1]))\.\d{1,3}\.\d{1,3})(:3000|:5173)?$",
]

# Asegura que el navegador permita enviar Authorization/CSRF si lo usas
CORS_ALLOW_HEADERS = list(default_headers) + [
    "authorization",
    "x-csrftoken",
]

# 🚩 IMPORTANTE: CSRF confía SOLO en lista explícita (no regex). La leemos de .env.
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=CORS_ALLOWED_ORIGINS,
)

if DEBUG:
    # Añade dinámicamente todos los posibles orígenes LAN (para pruebas en cualquier ciudad/red)
    trusted = set(CSRF_TRUSTED_ORIGINS) if isinstance(CSRF_TRUSTED_ORIGINS, list) else set(list(CSRF_TRUSTED_ORIGINS))
    try:
        hostname = socket.gethostname()
        local_ips = set(socket.gethostbyname_ex(hostname)[2])
        # Segmentos LAN comunes (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
        lan_prefixes = ["192.168", "10.", "172.16", "172.17", "172.18", "172.19", "172.20", "172.21", "172.22", "172.23", "172.24", "172.25", "172.26", "172.27", "172.28", "172.29", "172.30", "172.31"]
        for pre in lan_prefixes:
            for x in range(0, 256):
                ip = f"{pre}.{x}"
                trusted.add(f"http://{ip}:3000")
                trusted.add(f"http://{ip}:5173")
        # Agrega tus IPs locales reales
        for ip in local_ips:
            trusted.add(f"http://{ip}:3000")
            trusted.add(f"http://{ip}:5173")
        # El hostname local (útil si accedes por nombre en LAN)
        trusted.add(f"http://{hostname}:3000")
        trusted.add(f"http://{hostname}:5173")
        CSRF_TRUSTED_ORIGINS = list(trusted)
    except Exception as e:
        print("Error ampliando CSRF_TRUSTED_ORIGINS:", e)

# Cookies de sesión/CSRF para SPA en dev
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_NAME = "csrftoken"

# Configuración adicional para mejorar el manejo de sesiones
SESSION_COOKIE_AGE = 86400  # 24 horas
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_DOMAIN = None  # Permite cookies en localhost

# Si sirves detrás de proxy (ngrok/traefik), descomenta:
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# =========================
# URLs / Templates / WSGI
# =========================
APPEND_SLASH = True
ROOT_URLCONF = "core.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "core.wsgi.application"

# =========================
# Base de datos (dev)
# =========================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "dbtest.sqlite3",
    }
}

# =========================
# Passwords
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =========================
# i18n / TZ
# =========================
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# =========================
# Static / Media
# =========================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DATA_UPLOAD_MAX_MEMORY_SIZE = 32 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 32 * 1024 * 1024

# =========================
# DRF / OpenAPI (Swagger)
# =========================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API Registro de Camiones",
    "DESCRIPTION": "Backend (Django REST) para control de entradas y salidas con OCR (Google Vision).",
    "VERSION": "0.1.0",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True},
}

# =========================
# Celery (si lo usas en dev)
# =========================
CELERY_BROKER_URL = env("CELERY_BROKER", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_BACKEND", default="redis://localhost:6379/0")

# =========================
# Logging (verboso en dev)
# =========================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "DEBUG" if DEBUG else "INFO"},
    "loggers": {
        "django.request": {"level": "INFO", "handlers": ["console"], "propagate": True},
        "django.db.backends": {"level": "INFO" if DEBUG else "WARNING", "handlers": ["console"]},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
