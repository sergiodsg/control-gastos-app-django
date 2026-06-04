import os

if os.environ.get('DJANGO_USE_SQLITE', '').lower() not in ('1', 'true', 'yes'):
    import pymysql
    pymysql.install_as_MySQLdb()
