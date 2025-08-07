from __future__ import annotations

import os

from django_extensions.utils import InternalIPS

from .base import *

# Import these afterwards, to override
from resonant_settings.development.celery import *  # isort: skip
from resonant_settings.development.debug_toolbar import *  # isort: skip
from resonant_settings.development.minio_storage import *  # isort: skip

INSTALLED_APPS += [
    'debug_toolbar',
    'django_browser_reload',
]
# Force WhiteNoice to serve static files, even when using 'manage.py runserver_plus'
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

STORAGES['default'] = {
    'BACKEND': 'minio_storage.storage.MinioMediaStorage',
}
DANDI_DANDISETS_BUCKET_NAME = MINIO_STORAGE_MEDIA_BUCKET_NAME

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

# If this environment variable is set, the pydantic model will allow URLs with localhost
# in them. This is important for development and testing environments, where URLs will
# frequently point to localhost.
os.environ['DANDI_ALLOW_LOCALHOST_URLS'] = 'True'

DANDI_AUTO_APPROVE_USERS = True

DANDI_DEV_EMAIL = 'test-dev@example.com'
DANDI_ADMIN_EMAIL = 'test-admin@example.com'
