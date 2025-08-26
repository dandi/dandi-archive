from __future__ import annotations

from datetime import timedelta
import logging
from pathlib import Path
from typing import TYPE_CHECKING, cast
from urllib.parse import urlunparse

from corsheaders.defaults import default_headers
from dandischema.consts import DANDI_SCHEMA_VERSION as _DEFAULT_DANDI_SCHEMA_VERSION
import django_stubs_ext
from environ import Env
from resonant_settings.allauth import *
from resonant_settings.celery import *
from resonant_settings.django import *
from resonant_settings.django_extensions import *
from resonant_settings.logging import *
from resonant_settings.oauth_toolkit import *
from resonant_settings.rest_framework import *

if TYPE_CHECKING:
    from urllib.parse import ParseResult

django_stubs_ext.monkeypatch()

env = Env()

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent

ROOT_URLCONF = 'dandiapi.urls'

INSTALLED_APPS = [
    # Install local apps first, to ensure any overridden resources are found first
    'dandiapi.api.apps.PublishConfig',
    'dandiapi.search.apps.SearchConfig',
    'dandiapi.zarr.apps.ZarrConfig',
    # Apps with overrides
    'auth_style',
    'resonant_settings.allauth_support',
    # Everything else
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.messages',
    'django.contrib.postgres',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django_extensions',
    'django_filters',
    'drf_yasg',
    'guardian',
    'oauth2_provider',
    'resonant_utils',
    'rest_framework',
    'rest_framework.authtoken',
    's3_file_field',
]

MIDDLEWARE = [
    # CorsMiddleware must be added before other response-generating middleware,
    # so it can potentially add CORS headers to those responses too.
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoiseMiddleware must be directly after SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # GZipMiddleware can be after WhiteNoiseMiddleware, as WhiteNoise performs its own compression
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# Internal datetimes are timezone-aware, so this only affects rendering and form input
TIME_ZONE = 'UTC'
# https://docs.djangoproject.com/en/4.2/ref/settings/#std-setting-USE_TZ
# TODO: this defaults to True starting with Django 5. Remove this when we upgrade
USE_TZ = True

DATABASES = {
    'default': {
        **env.db_url('DJANGO_DATABASE_URL', engine='django.db.backends.postgresql'),
        'CONN_MAX_AGE': timedelta(minutes=10).total_seconds(),
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STORAGES = {
    # Inject the "default" storage in particular run configurations
    'staticfiles': {
        # CompressedManifestStaticFilesStorage does not work properly with drf-
        # https://github.com/axnsan12/drf-yasg/issues/761
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}
DANDI_DANDISETS_BUCKET_NAME: str
DANDI_DANDISETS_BUCKET_PREFIX: str = env.str('DJANGO_DANDI_DANDISETS_BUCKET_PREFIX', default='')

STATIC_ROOT = BASE_DIR / 'staticfiles'
# Django staticfiles auto-creates any intermediate directories, but do so here to prevent warnings.
STATIC_ROOT.mkdir(exist_ok=True)

# Django's docs suggest that STATIC_URL should be a relative path,
# for convenience serving a site on a subpath.
STATIC_URL = 'static/'

# Make Django and Allauth redirects consistent, but both may be changed.
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'

CORS_ALLOWED_ORIGINS: list[str] = env.list('DJANGO_CORS_ALLOWED_ORIGINS', cast=str, default=[])
CORS_ALLOWED_ORIGIN_REGEXES: list[str] = env.list(
    'DJANGO_CORS_ALLOWED_ORIGIN_REGEXES', cast=str, default=[]
)

# Needed for Sentry Performance to work in frontend
CORS_ALLOW_HEADERS = (*default_headers, 'baggage', 'sentry-trace')

# Registration will occur via GitHub, which already verifies email addresses.
ACCOUNT_EMAIL_VERIFICATION = 'none'
# Don't require a POST request to initiate a GitHub login
# https://github.com/pennersr/django-allauth/blob/HEAD/ChangeLog.rst#backwards-incompatible-changes-2
SOCIALACCOUNT_LOGIN_ON_GET = True

AUTHENTICATION_BACKENDS += ['guardian.backends.ObjectPermissionBackend']

REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += [
    'rest_framework.authentication.TokenAuthentication'
]
REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] += ['dandiapi.api.permissions.IsApprovedOrReadOnly']
REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS'] = 'dandiapi.api.views.pagination.DandiPagination'
REST_FRAMEWORK['EXCEPTION_HANDLER'] = 'dandiapi.drf_utils.rewrap_django_core_exceptions'

REST_FRAMEWORK_EXTENSIONS = {'DEFAULT_PARENT_LOOKUP_KWARG_NAME_PREFIX': ''}

# Clearing out the stock `SWAGGER_SETTINGS` variable causes a Django login
# button to appear in Swagger, along with a spurious "authorize" button that
# doesn't work. This at least enables us to authorize to the Swagger page on
# the spot, which is quite useful.
SWAGGER_SETTINGS = {
    'DEFAULT_AUTO_SCHEMA_CLASS': 'dandiapi.swagger.DANDISwaggerAutoSchema',
}


# The CloudAMQP connection was dying, using the heartbeat should keep it alive
CELERY_BROKER_HEARTBEAT = 20
# Allow this to be configurable, but keep the default as the number of CPU cores
CELERY_WORKER_CONCURRENCY: int | None = env.int('DJANGO_CELERY_WORKER_CONCURRENCY', default=None)

_dandi_log_level: str = env.str('DJANGO_DANDI_LOG_LEVEL', default='INFO')
# Configure the logging level on all DANDI loggers.
logging.getLogger('dandiapi').setLevel(_dandi_log_level)

# Configure custom logging to log username if request is associated
# with a user
LOGGING['handlers']['console']['class'] = 'dandiapi.api.logging.DandiHandler'
MIDDLEWARE += [
    'dandiapi.api.logging.RequestUserMiddleware',
]

# This is where the schema version should be set.
# It can optionally be overwritten with the environment variable, but that should only be
# considered a temporary fix.
DANDI_SCHEMA_VERSION: str = env.str(
    'DJANGO_DANDI_SCHEMA_VERSION', default=_DEFAULT_DANDI_SCHEMA_VERSION
)

DANDI_ZARR_PREFIX_NAME: str = env.str('DJANGO_DANDI_ZARR_PREFIX_NAME', default='zarr')

# Required environment variables
DANDI_WEB_APP_URL = urlunparse(cast('ParseResult', env.url('DJANGO_DANDI_WEB_APP_URL')))
DANDI_API_URL = urlunparse(cast('ParseResult', env.url('DJANGO_DANDI_API_URL')))
DANDI_JUPYTERHUB_URL = urlunparse(cast('ParseResult', env.url('DJANGO_DANDI_JUPYTERHUB_URL')))

_dandi_doi_api_url = cast('ParseResult | None', env.url('DJANGO_DANDI_DOI_API_URL', default=None))
DANDI_DOI_API_URL: str | None = urlunparse(_dandi_doi_api_url) if _dandi_doi_api_url else None
DANDI_DOI_API_USER: str | None = env.str('DJANGO_DANDI_DOI_API_USER', default=None)
DANDI_DOI_API_PASSWORD: str | None = env.str('DJANGO_DANDI_DOI_API_PASSWORD', default=None)
DANDI_DOI_API_PREFIX: str | None = env.str('DJANGO_DANDI_DOI_API_PREFIX', default=None)
DANDI_DOI_PUBLISH: bool = env.bool('DJANGO_DANDI_DOI_PUBLISH', default=False)

DANDI_VALIDATION_JOB_INTERVAL: int = env.int('DJANGO_DANDI_VALIDATION_JOB_INTERVAL', default=60)

DANDI_AUTO_APPROVE_USERS = False

DANDI_DEV_EMAIL: str
DANDI_ADMIN_EMAIL: str
