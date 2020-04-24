import os

from celery import Celery
import configurations.importer

os.environ['DJANGO_SETTINGS_MODULE'] = 'dandi.settings'
if not os.environ.get('DANDI_CONFIGURATION'):
    raise ValueError('The environment variable "DANDI_CONFIGURATION" must be set.')
configurations.importer.ConfigurationImporter.namevar = 'DANDI_CONFIGURATION'
configurations.importer.install()

# Using a string config_source means the worker doesn't have to serialize
# the configuration object to child processes.
app = Celery(
    'dandi',
    config_source='django.conf:settings',
    namespace='CELERY'
)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
