release: ./manage.py migrate
web: gunicorn --bind 0.0.0.0:$PORT dandiapi.wsgi
# celery-beat: REMAP_SIGTERM=SIGQUIT celery --app dandiapi.celery beat --loglevel INFO
# Rather than using a dedicated worker for Celery Beat, we simply use the -B option on the priority task worker.
# This means that we cannot safely scale up the number of priority-workers without Celery Beat triggering multiple events.
# This is OK for now because of how lightweight all high priority tasks currently are,
# but we may need to switch back to a dedicated worker in the future.
# The queue `celery` is the default queue.
worker: REMAP_SIGTERM=SIGQUIT celery --app dandiapi.celery worker --loglevel INFO -Q celery -B
checksum-worker: REMAP_SIGTERM=SIGQUIT celery --app dandiapi.celery worker --loglevel INFO -Q calculate_sha256
# Manifests can be very memory intensive for large numbers of assets, so limit concurrency to 1
manifest-worker: REMAP_SIGTERM=SIGQUIT celery --app dandiapi.celery worker --loglevel INFO -Q write_manifest_files -c 1
