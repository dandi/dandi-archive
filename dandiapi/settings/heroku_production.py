from __future__ import annotations

import os

# Redefine these before importing the rest of the settings
os.environ['DJANGO_DATABASE_URL'] = os.environ['DATABASE_URL']
os.environ['DJANGO_CELERY_BROKER_URL'] = os.environ['CLOUDAMQP_URL']
# Provided by https://github.com/ianpurvis/heroku-buildpack-version
os.environ['DJANGO_SENTRY_RELEASE'] = os.environ['SOURCE_VERSION']

from .production import *  # isort: skip

# This needs to be set by the HTTPS terminating reverse proxy.
# Heroku and Render automatically set this.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
