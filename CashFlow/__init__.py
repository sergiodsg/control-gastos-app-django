import os
import sys
from types import ModuleType
from pathlib import Path

# Por defecto usamos SQLite para evitar dependencias de MySQL, 
# a menos que se especifique lo contrario via env var.
USE_SQLITE = os.environ.get('USE_SQLITE', 'True').lower() in ('true', '1', 'yes')

if USE_SQLITE:
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # Creamos un módulo ficticio para 'CashFlow.db' para evitar modificar db.py
    db_mock = ModuleType('CashFlow.db')
    db_mock.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    # Inyectamos el mock en sys.modules antes de que settings.py lo importe
    sys.modules['CashFlow.db'] = db_mock

    # Parcheamos ALLOWED_HOSTS dinámicamente sin tocar settings.py
    try:
        from . import settings as settings_mod
        hosts_to_add = ['127.0.0.1', 'localhost', '0.0.0.0']
        for host in hosts_to_add:
            if host not in settings_mod.ALLOWED_HOSTS:
                settings_mod.ALLOWED_HOSTS.append(host)
    except Exception:
        pass
else:
    try:
        import pymysql
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
