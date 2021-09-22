release: ./manage.py migrate
web: gunicorn --bind 0.0.0.0:$PORT dandiapi.wsgi
# We are using the -B flag to launch the beat scheduler within the worker thread
# This means that we cannot have multiple workers, as they would all trigger beat events
# The alternative would be a separate worker to drive the beat, which is costly at our current Heroku dyno tier
worker: REMAP_SIGTERM=SIGQUIT celery --app dandiapi.celery worker --loglevel INFO -B
