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

from .db import DATABASES

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# Seguridad
# -----------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-dev-only-change-in-production',
)

DEBUG = False
ALLOWED_HOSTS = [ 'cashflow.cpaldaca.com', 'dev.cpaldaca.com', 'localhost', '127.0.0.1', 'www.cashflow.cpaldaca.com' ]

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

DATABASES = DATABASES

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
# Desarrollo / Producción
# -----------------------------------------------------------------------------

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')   

LOG_LEVEL = os.environ.get(
    'DJANGO_LOG_LEVEL',
    'DEBUG' if IS_DEVELOPMENT else 'WARNING',
)
LOG_DIR = Path(os.environ.get('DJANGO_LOG_DIR', BASE_DIR / 'logs'))
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{levelname}] {name}: {message}',
            'style': '{',
        },
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {module}:{lineno} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'app_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'app.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'verbose',
            'level': LOG_LEVEL,
        },
        'server_errors_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'server_errors.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 10,
            'encoding': 'utf-8',
            'formatter': 'verbose',
            'level': 'ERROR',
        },
        'transactions_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'transactions.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 10,
            'encoding': 'utf-8',
            'formatter': 'verbose',
            'level': LOG_LEVEL,
        },
        'application_errors_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'application_errors.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 10,
            'encoding': 'utf-8',
            'formatter': 'verbose',
            'level': 'WARNING',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'app_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'server_errors_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'server_errors_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'cashflow.debug': {
            'handlers': ['console', 'app_file', 'application_errors_file'],
            'level': 'DEBUG' if IS_DEVELOPMENT else 'INFO',
            'propagate': False,
        },
        'cashflow.transactions': {
            'handlers': ['console', 'transactions_file', 'application_errors_file'],
            'level': 'DEBUG' if IS_DEVELOPMENT else 'INFO',
            'propagate': False,
        },
        'cashflow.errors': {
            'handlers': ['console', 'application_errors_file', 'server_errors_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'cashflow.accounts': {
            'handlers': ['console', 'app_file', 'application_errors_file'],
            'level': 'DEBUG' if IS_DEVELOPMENT else 'INFO',
            'propagate': False,
        },
    },
}

# En producción: sin consola (stderr bloquea workers LiteSpeed/LSAPI)
if IS_PRODUCTION:
    _APP_LOG_HANDLERS = ['app_file', 'application_errors_file']
    _TX_LOG_HANDLERS = ['transactions_file', 'application_errors_file']
    _ERR_LOG_HANDLERS = ['application_errors_file', 'server_errors_file']
    LOGGING['loggers']['django']['handlers'] = ['app_file']
    LOGGING['loggers']['django.request']['handlers'] = ['server_errors_file']
    LOGGING['loggers']['django.server']['handlers'] = ['server_errors_file']
    LOGGING['loggers']['cashflow.debug']['handlers'] = _APP_LOG_HANDLERS
    LOGGING['loggers']['cashflow.transactions']['handlers'] = _TX_LOG_HANDLERS
    LOGGING['loggers']['cashflow.errors']['handlers'] = _ERR_LOG_HANDLERS
    LOGGING['loggers']['cashflow.accounts']['handlers'] = _APP_LOG_HANDLERS

# Log de consultas SQL en consola (opcional: DJANGO_SQL_LOG=1)
if IS_DEVELOPMENT and os.environ.get('DJANGO_SQL_LOG', '').lower() in ('1', 'true', 'yes'):
    LOGGING['loggers']['django.db.backends'] = {
        'handlers': ['console'],
        'level': 'DEBUG',
        'propagate': False,
    }
