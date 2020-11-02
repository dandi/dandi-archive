release: ./manage.py migrate
web: gunicorn --bind 0.0.0.0:$PORT dandiapi.wsgi
worker: REMAP_SIGTERM=SIGQUIT celery worker --app dandiapi.celery --loglevel info --without-heartbeat
