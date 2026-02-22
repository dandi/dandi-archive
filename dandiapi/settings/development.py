from __future__ import annotations

from django_extensions.utils import InternalIPS

from .base import *

# Import these afterwards, to override
from resonant_settings.development.celery import *  # isort: skip
from resonant_settings.development.debug_toolbar import *  # isort: skip

INSTALLED_APPS += [
    'debug_toolbar',
    'django_browser_reload',
]
# Force WhiteNoise to serve static files, even when using 'manage.py runserver_plus'
staticfiles_index = INSTALLED_APPS.index('django.contrib.staticfiles')
INSTALLED_APPS.insert(staticfiles_index, 'whitenoise.runserver_nostatic')

# Include Debug Toolbar middleware as early as possible in the list.
# However, it must come after any other middleware that encodes the response's content,
# such as GZipMiddleware.
MIDDLEWARE.insert(
    MIDDLEWARE.index('django.middleware.gzip.GZipMiddleware') + 1,
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)
# Should be listed after middleware that encode the response.
MIDDLEWARE += [
    'django_browser_reload.middleware.BrowserReloadMiddleware',
]

# DEBUG is not enabled for testing, to maintain parity with production.
# Also, do not directly reference DEBUG when toggling application features; it's more sustainable
# to add new settings as individual feature flags.
DEBUG = True

SECRET_KEY = 'insecure-secret'  # noqa: S105

# This is typically only overridden when running from Docker.
INTERNAL_IPS = InternalIPS(env.list('DJANGO_INTERNAL_IPS', cast=str, default=['127.0.0.1']))
CORS_ALLOWED_ORIGIN_REGEXES = env.list(
    'DJANGO_CORS_ALLOWED_ORIGIN_REGEXES',
    cast=str,
    default=[r'^http://localhost:\d+$', r'^http://127\.0\.0\.1:\d+$'],
)

_minio_url: ParseResult = env.url('DJANGO_MINIO_STORAGE_URL')
_storage_media_url: ParseResult | None = env.url('DJANGO_MINIO_STORAGE_MEDIA_URL', None)
STORAGES['default'] = {
    'BACKEND': 'dandiapi.storage.MinioDandiS3Storage',
    'OPTIONS': {
        'endpoint_url': f'{_minio_url.scheme}://{_minio_url.hostname}:{_minio_url.port}',
        'access_key': _minio_url.username,
        'secret_key': _minio_url.password,
        'bucket_name': _minio_url.path.lstrip('/'),
        'querystring_expire': int(timedelta(hours=6).total_seconds()),
        'media_url': _storage_media_url,
    },
}
DANDI_DANDISETS_BUCKET_NAME = STORAGES['default']['OPTIONS']['bucket_name']  # TODO: remove

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

OAUTH2_PROVIDER['ALLOWED_REDIRECT_URI_SCHEMES'] = ['http', 'https']
# In development, always present the approval dialog
OAUTH2_PROVIDER['REQUEST_APPROVAL_PROMPT'] = 'force'

SHELL_PLUS_IMPORTS = [
    'from dandiapi.api import tasks',
    'from dandiapi.api.mail import *',
]

# This allows django-debug-toolbar to run in swagger and show the last made request
DEBUG_TOOLBAR_CONFIG['UPDATE_ON_FETCH'] = True

DANDI_AUTO_APPROVE_USERS = True

DANDI_DEV_EMAIL = 'test-dev@example.com'
DANDI_ADMIN_EMAIL = 'test-admin@example.com'
