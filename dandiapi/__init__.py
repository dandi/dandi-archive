# Dummy change
from __future__ import annotations

from importlib.metadata import version
import logging

from django.conf import settings

# This project module is imported for us when Django starts. To ensure that Celery app is always
# defined prior to any shared_task definitions (so those tasks will bind to the app), import
# the Celery module here for side effects.
from .celery import app as _celery_app  # noqa: F401

__version__ = version('dandiapi')

# Configure the logging level on all DANDI loggers.
logging.getLogger(__name__).setLevel(settings.DANDI_LOG_LEVEL)
