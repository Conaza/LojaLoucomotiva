"""Django settings for Loucomotiva store."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', '').strip()
DEBUG = os.getenv('DEBUG', 'False').strip().lower() in ('1', 'true', 'yes', 'on')

if not SECRET_KEY or (not DEBUG and SECRET_KEY in ('change-me', 'changeme')):
    raise ImproperlyConfigured(
        'SECRET_KEY must be set in .env. Use a strong random value; '
        'do not use change-me when DEBUG=False.'
    )

ALLOWED_HOSTS = []
for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(','):
    host = host.strip()
    if not host:
        continue
    # Django's subdomain wildcard is a leading dot. "*.vercel.app" is not.
    if host.startswith('*.'):
        host = '.' + host[2:]
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

# Preview URLs (loja-….vercel.app) change on every deploy. Vercel sets VERCEL=1.
if os.getenv('VERCEL') and '.vercel.app' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('.vercel.app')

if DEBUG and 'testserver' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('testserver')

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]
if os.getenv('VERCEL') and 'https://*.vercel.app' not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append('https://*.vercel.app')

MAX_QTD_ITEM = 20
MAX_PEDIDOS_POR_HORA = 10

# Pagamentos via checkout InfinitePay — veja docs/INTEGRACAO_INFINITEPAY.md
# InfiniteTag da conta, sem o "$" inicial.
INFINITEPAY_HANDLE = os.getenv('INFINITEPAY_HANDLE', '').strip().lstrip('$')
INFINITEPAY_API_URL = os.getenv(
    'INFINITEPAY_API_URL', 'https://api.checkout.infinitepay.io',
).strip()
INFINITEPAY_WEBHOOK_TOKEN = os.getenv('INFINITEPAY_WEBHOOK_TOKEN', '').strip()
# URL pública do site (ex.: https://loja.exemplo.com), usada no retorno e no webhook.
SITE_URL = os.getenv('SITE_URL', '').strip().rstrip('/')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'produtos',
    'carrinho',
    'pedidos',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
                'carrinho.context_processors.carrinho_resumo',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DB_OPTIONS = {'charset': 'utf8mb4'}
DB_SSL = os.getenv('DB_SSL', 'False').strip().lower() in ('1', 'true', 'yes', 'on')
if DB_SSL:
    # Enable for remote MySQL (Aiven and similar). Keep False for local MySQL.
    DB_OPTIONS['ssl'] = {'ssl_mode': 'REQUIRED'}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'loucomotiva'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': DB_OPTIONS,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
MAX_PRODUTO_IMAGE_BYTES = 1 * 1024 * 1024
MAX_PRODUTO_IMAGES = 8
MAX_PRODUTO_UPLOAD_BYTES = 4 * 1024 * 1024
if DEBUG:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
else:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

from django.contrib.messages import constants as message_constants

MESSAGE_TAGS = {
    message_constants.DEBUG: 'secondary',
    message_constants.INFO: 'info',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.ERROR: 'danger',
}


LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/admin-pedidos/'
LOGOUT_REDIRECT_URL = '/'

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 2 weeks
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
