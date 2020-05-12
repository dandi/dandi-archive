release: ./manage.py migrate
web: gunicorn --bind 0.0.0.0:$PORT dandi.wsgi
worker: REMAP_SIGTERM=SIGQUIT celery worker --app dandi.celery --loglevel info --without-heartbeat
