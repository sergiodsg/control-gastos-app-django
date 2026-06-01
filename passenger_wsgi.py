import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CashFlow.settings')

from CashFlow.wsgi import application
