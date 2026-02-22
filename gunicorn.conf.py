from __future__ import annotations

import os

from gunicorn.config import AccessLogFormat

bind = f'0.0.0.0:{os.environ.get("PORT", "8000")}'

# Set `graceful_timeout` to shorter than the 30 second limit imposed by Heroku restarts
graceful_timeout = 25

# Set `timeout` to shorter than the 30 second limit imposed by the Heroku router
timeout = 15

# Add the username to the access log (set by Django middleware)
access_log_format = AccessLogFormat.default + ' <username:%({x-request-username}o)s>'
