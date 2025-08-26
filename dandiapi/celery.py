from __future__ import annotations

from celery import Celery, signals

# Using a string config_source means the worker doesn't have to serialize
# the configuration object to child processes.
app = Celery(config_source='django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@signals.import_modules.connect
def _register_scheduled_tasks(sender, **kwargs):
    from dandiapi.api.tasks.scheduled import register_scheduled_tasks

    register_scheduled_tasks(sender, **kwargs)
