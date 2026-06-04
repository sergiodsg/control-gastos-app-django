import os

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
