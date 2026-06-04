import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _use_sqlite() -> bool:
    return os.environ.get('DJANGO_USE_SQLITE', '').lower() in ('1', 'true', 'yes')


if _use_sqlite():
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / os.environ.get('SQLITE_DB_NAME', 'test_db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'cashflow_db'),
            'USER': os.environ.get('DB_USER', 'RAG'),
            'PASSWORD': os.environ.get('DB_PASSWORD', '12345'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
            },
        }
    }
