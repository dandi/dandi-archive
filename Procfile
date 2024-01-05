release: ./manage.py migrate --fake
web: gunicorn --bind 0.0.0.0:$PORT dandiapi.wsgi --timeout 25
# celery-beat: REMAP_SIGTERM=SIGQUIT celery --app dandiapi.celery beat --loglevel INFO
# Rather than using a dedicated worker for Celery Beat, we simply use the -B option on the priority task worker.
# This means that we cannot safely scale up the number of priority-workers without Celery Beat triggering multiple events.
# This is OK for now because of how lightweight all high priority tasks currently are,
# but we may need to switch back to a dedicated worker in the future.
# The queue `celery` is the default queue.
worker: REMAP_SIGTERM=SIGQUIT celery --app dandiapi.celery worker --loglevel INFO -Q celery -B
# The checksum-worker calculates blob checksums and updates zarr checksum files
checksum-worker: REMAP_SIGTERM=SIGQUIT celery --app dandiapi.celery worker --loglevel INFO -Q calculate_sha256,ingest_zarr_archive
# The analytics-worker processes s3 log files serially
analytics-worker: REMAP_SIGTERM=SIGQUIT celery --app dandiapi.celery worker --loglevel INFO --concurrency 1 -Q s3-log-processing
