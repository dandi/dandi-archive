release: ./manage.py migrate
web: gunicorn --bind 0.0.0.0:$PORT dandiapi.wsgi
worker: REMAP_SIGTERM=SIGQUIT celery --app dandiapi.celery worker --loglevel INFO --beat --scheduler django_celery_beat.schedulers:DatabaseScheduler
