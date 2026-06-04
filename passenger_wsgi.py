import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Producción en Namecheap (LiteSpeed + Passenger)
os.environ.setdefault('DJANGO_ENV', 'production')
os.environ.setdefault('DEBUG', '0')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CashFlow.settings')

from CashFlow.wsgi import application
