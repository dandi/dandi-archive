from __future__ import annotations

import logging

import sentry_sdk
import sentry_sdk.integrations.celery
import sentry_sdk.integrations.django
import sentry_sdk.integrations.logging
import sentry_sdk.integrations.pure_eval

from ._sentry_utils import get_sentry_performance_sample_rate
from .base import *

# Import these afterwards, to override
from resonant_settings.production.email import *  # isort: skip
from resonant_settings.production.https import *  # isort: skip

SECRET_KEY: str = env.str('DJANGO_SECRET_KEY')

INSTALLED_APPS += [
    'allauth.socialaccount.providers.github',
]
# All login attempts in production should go straight to GitHub
LOGIN_URL = '/accounts/github/login/'
# Only allow GitHub auth on production, no username/password
SOCIALACCOUNT_ONLY = True

# This only needs to be defined in production. Testing will add 'testserver'. In development
# (specifically when DEBUG is True), 'localhost' and '127.0.0.1' will be added.
ALLOWED_HOSTS: list[str] = env.list('DJANGO_ALLOWED_HOSTS', cast=str)

DANDI_DANDISETS_BUCKET_NAME: str = env.str('DJANGO_STORAGE_BUCKET_NAME')
STORAGES['default'] = {
    'BACKEND': 'dandiapi.storage.DandiS3Storage',
    'OPTIONS': {
        'region_name': env.str('AWS_DEFAULT_REGION'),
        'access_key': env.str('AWS_ACCESS_KEY_ID'),
        'secret_key': env.str('AWS_SECRET_ACCESS_KEY'),
        'bucket_name': DANDI_DANDISETS_BUCKET_NAME,
        'querystring_expire': int(timedelta(hours=6).total_seconds()),
        'max_memory_size': 5 * 1024 * 1024,
    },
}

# In production, enable rate limiting for unauthenticated users
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '500/minute',
}


DANDI_DEV_EMAIL: str = env.str('DJANGO_DANDI_DEV_EMAIL')
DANDI_ADMIN_EMAIL: str = env.str('DJANGO_DANDI_ADMIN_EMAIL')

# sentry_sdk is able to directly use environment variables like 'SENTRY_DSN', but prefix them
# with 'DJANGO_' to avoid conflicts with other Sentry-using services.
sentry_sdk.init(
    dsn=env.str('DJANGO_SENTRY_DSN', default=None),
    environment=env.str('DJANGO_SENTRY_ENVIRONMENT', default=None),
    release=env.str('DJANGO_SENTRY_RELEASE', default=None),
    integrations=[
        sentry_sdk.integrations.logging.LoggingIntegration(
            level=logging.INFO,
            event_level=logging.WARNING,
        ),
        sentry_sdk.integrations.django.DjangoIntegration(),
        sentry_sdk.integrations.celery.CeleryIntegration(),
        sentry_sdk.integrations.pure_eval.PureEvalIntegration(),
    ],
    # "project_root" defaults to the CWD, but for safety, don't assume that will be set correctly
    project_root=str(BASE_DIR),
    # Send traces for non-exception events too
    attach_stacktrace=True,
    # Submit request User info from Django
    send_default_pii=True,
    traces_sampler=get_sentry_performance_sample_rate,
    profiles_sampler=get_sentry_performance_sample_rate,
)
