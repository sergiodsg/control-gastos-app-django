import os

os.environ.setdefault('DJANGO_ENV', 'development')
if os.environ.get('DJANGO_ENV') == 'development':
    os.environ.setdefault('DJANGO_USE_SQLITE', '1')

if os.environ.get('DJANGO_USE_SQLITE', '').lower() not in ('1', 'true', 'yes'):
    import pymysql
    pymysql.install_as_MySQLdb()
