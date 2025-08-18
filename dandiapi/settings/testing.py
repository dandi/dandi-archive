from __future__ import annotations

from .base import *

# Import these afterwards, to override
from resonant_settings.development.minio_storage import *  # isort: skip

SECRET_KEY = 'insecure-secret'  # noqa: S105

# Use a fast, insecure hasher to speed up tests
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

STORAGES['default'] = {
    'BACKEND': 'minio_storage.storage.MinioMediaStorage',
}
MINIO_STORAGE_MEDIA_BUCKET_NAME = 'test-django-storage'
DANDI_DANDISETS_BUCKET_NAME = MINIO_STORAGE_MEDIA_BUCKET_NAME
DANDI_DANDISETS_BUCKET_PREFIX = 'test-prefix/'

# Testing will set EMAIL_BACKEND to use the memory backend

# Run celery tasks synchronously in tests
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ALWAYS_EAGER = True

DANDI_ZARR_PREFIX_NAME = 'test-zarr'

DANDI_JUPYTERHUB_URL = 'https://hub.dandiarchive.org/'

DANDI_DEV_EMAIL = 'test-dev@example.com'
DANDI_ADMIN_EMAIL = 'test-admin@example.com'
