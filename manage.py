#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

os.environ.setdefault('DJANGO_ENV', 'development')
if os.environ.get('DJANGO_ENV') == 'development':
    os.environ.setdefault('DJANGO_USE_SQLITE', '1')

if os.environ.get('DJANGO_USE_SQLITE', '').lower() not in ('1', 'true', 'yes'):
    import pymysql
    pymysql.install_as_MySQLdb()


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CashFlow.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
