from __future__ import annotations

import os

# Redefine these before importing the rest of the settings
os.environ['DJANGO_DATABASE_URL'] = os.environ['DATABASE_URL']
os.environ['DJANGO_CELERY_BROKER_URL'] = os.environ['CLOUDAMQP_URL']
# Provided by the Heroku Key-Value Store add-on
os.environ['DJANGO_CACHE_URL'] = os.environ['REDIS_URL']
# Provided by https://github.com/ianpurvis/heroku-buildpack-version
os.environ['DJANGO_SENTRY_RELEASE'] = os.environ['SOURCE_VERSION']

from .production import *

# This needs to be set by the HTTPS terminating reverse proxy.
# Heroku and Render automatically set this.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Inform rate limiting that "X-Forwarded-For" should be trusted, as it's appended by Heroku.
ALLAUTH_TRUSTED_PROXY_COUNT = 1
# Likewise, inform DRF throttling that the last entry of "X-Forwarded-For" is the client address
# which Heroku appended. Without this, clients can evade rate limiting by sending the header
# themselves, as DRF would otherwise identify clients by the entire (client controlled) header.
REST_FRAMEWORK['NUM_PROXIES'] = 1

# Heroku's Key-Value Store terminates TLS with a self-signed certificate, which can't be verified.
if CACHES['default']['LOCATION'].startswith('rediss://'):
    CACHES['default']['OPTIONS']['ssl_cert_reqs'] = None
