"""
Django settings for CashFlow.

Entorno por defecto: desarrollo (`DJANGO_ENV=development`).
En producción: `DJANGO_ENV=production` y variables de entorno para BD y SECRET_KEY.
"""
import os
from pathlib import Path

# Entorno: development | production
DJANGO_ENV = os.environ.get('DJANGO_ENV', 'development').lower()
IS_DEVELOPMENT = DJANGO_ENV == 'development'

# En desarrollo, SQLite por defecto (sin MySQL). Para MySQL local: DJANGO_USE_SQLITE=0
if IS_DEVELOPMENT:
    os.environ.setdefault('DJANGO_USE_SQLITE', '1')

from .db import DATABASES

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# Seguridad
# -----------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-dev-only-change-in-production',
)

DEBUG = os.environ.get('DEBUG', '1' if IS_DEVELOPMENT else '0').lower() in ('1', 'true', 'yes')

if IS_DEVELOPMENT:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'testserver']
else:
    ALLOWED_HOSTS = [
        h.strip()
        for h in os.environ.get(
            'ALLOWED_HOSTS',
            'localhost,127.0.0.1,.onrender.com,cashflow.cpaldaca.com,dev.cpaldaca.com',
        ).split(',')
        if h.strip()
    ]

# -----------------------------------------------------------------------------
# Aplicaciones
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'organizations',
    'BCV',
    'superadmin_panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'superadmin_panel.middleware.SuperuserPanelMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'CashFlow.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'superadmin_panel.context_processors.superadmin_panel',
            ],
        },
    },
]

WSGI_APPLICATION = 'CashFlow.wsgi.application'

# -----------------------------------------------------------------------------
# Base de datos (definida en db.py)
# -----------------------------------------------------------------------------
# DATABASES importado arriba

# -----------------------------------------------------------------------------
# Validación de contraseñas
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -----------------------------------------------------------------------------
# Internacionalización
# -----------------------------------------------------------------------------
LANGUAGE_CODE = 'es-ve'

TIME_ZONE = 'America/Caracas'

USE_I18N = True

USE_TZ = True

# -----------------------------------------------------------------------------
# Archivos estáticos
# -----------------------------------------------------------------------------
STATIC_URL = '/static/'

# Origen de estáticos del proyecto (CSS/JS en static/)
STATICFILES_DIRS = [BASE_DIR / 'static']

# Destino de collectstatic (no debe ser la misma carpeta que STATICFILES_DIRS)
STATIC_ROOT = BASE_DIR / 'staticfiles'

if IS_DEVELOPMENT:
    # Sirve desde static/ sin ejecutar collectstatic en cada cambio
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
    WHITENOISE_USE_FINDERS = True
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    WHITENOISE_USE_FINDERS = False

# -----------------------------------------------------------------------------
# Auth
# -----------------------------------------------------------------------------
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'
LOGIN_URL = 'login'

# -----------------------------------------------------------------------------
# Desarrollo
# -----------------------------------------------------------------------------
if IS_DEVELOPMENT:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

    # Cookies menos estrictas en local (HTTP)
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

    INTERNAL_IPS = ['127.0.0.1', '::1']

    # Log de consultas SQL en consola (opcional: DJANGO_SQL_LOG=1)
    if os.environ.get('DJANGO_SQL_LOG', '').lower() in ('1', 'true', 'yes'):
        LOGGING = {
            'version': 1,
            'disable_existing_loggers': False,
            'handlers': {
                'console': {'class': 'logging.StreamHandler'},
            },
            'loggers': {
                'django.db.backends': {
                    'handlers': ['console'],
                    'level': 'DEBUG',
                },
            },
        }
