from __future__ import annotations

from .base import *

SECRET_KEY = 'insecure-secret'  # noqa: S105

# Use a fast, insecure hasher to speed up tests
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

_minio_url: ParseResult = env.url('DJANGO_MINIO_STORAGE_URL')
STORAGES['default'] = {
    'BACKEND': 'dandiapi.storage.MinioDandiS3Storage',
    'OPTIONS': {
        'endpoint_url': f'{_minio_url.scheme}://{_minio_url.hostname}:{_minio_url.port}',
        'access_key': _minio_url.username,
        'secret_key': _minio_url.password,
        'bucket_name': 'test-django-storage',
        'querystring_expire': int(timedelta(hours=6).total_seconds()),
    },
}
DANDI_DANDISETS_BUCKET_NAME = 'test-django-storage'
DANDI_DANDISETS_BUCKET_PREFIX = 'test-prefix/'

# Testing will set EMAIL_BACKEND to use the memory backend

# Run celery tasks synchronously in tests
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ALWAYS_EAGER = True

DANDI_ZARR_PREFIX_NAME = 'test-zarr'

DANDI_JUPYTERHUB_URL = 'https://hub.dandiarchive.org/'

DANDI_DEV_EMAIL = 'test-dev@example.com'
DANDI_ADMIN_EMAIL = 'test-admin@example.com'
