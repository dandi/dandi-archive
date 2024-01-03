from __future__ import annotations
import os

from celery import Celery, signals
import celery.app.trace
import configurations.importer

celery.app.trace.LOG_RECEIVED = """\
Task %(name)s[%(id)s] received: (%(args)s, %(kwargs)s)\
"""

os.environ['DJANGO_SETTINGS_MODULE'] = 'dandiapi.settings'
if not os.environ.get('DJANGO_CONFIGURATION'):
    raise ValueError('The environment variable "DJANGO_CONFIGURATION" must be set.')
configurations.importer.install()

# Using a string config_source means the worker doesn't have to serialize
# the configuration object to child processes.
app = Celery(config_source='django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@signals.import_modules.connect
def _register_scheduled_tasks(sender, **kwargs):
    from dandiapi.api.tasks.scheduled import register_scheduled_tasks

    register_scheduled_tasks(sender, **kwargs)
