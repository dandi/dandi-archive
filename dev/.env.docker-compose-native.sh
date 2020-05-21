# This file must be sourced, not run
vars='
DJANGO_CONFIGURATION=DevelopmentConfiguration
DJANGO_DATABASE_URL=postgres://postgres:postgres@localhost:5432/dandi
DJANGO_CELERY_BROKER_URL=amqp://localhost:5672/
DJANGO_MINIO_STORAGE_ENDPOINT=localhost:9000
DJANGO_MINIO_STORAGE_ACCESS_KEY=minioAdminAccessKey
DJANGO_MINIO_STORAGE_SECRET_KEY=minioAdminSecretKey
DJANGO_STORAGE_BUCKET_NAME=dandi-files
DJANGO_DANDISETS_BUCKET_NAME=dandi-dandisets
'
for var in $vars; do export "${var}"; done
