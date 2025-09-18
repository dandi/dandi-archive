from __future__ import annotations

import os

from gunicorn.config import AccessLogFormat

bind = f'0.0.0.0:{os.environ.get("PORT", "8000")}'

# Explicitly set the timeout to 5 seconds less than the Heroku request timeout so
# that gunicorn can gracefully shut down the worker if a request times out.
timeout = 25

# Add the username to the access log (set by Django middleware)
access_log_format = AccessLogFormat.default + ' <username:%({x-request-username}o)s>'
