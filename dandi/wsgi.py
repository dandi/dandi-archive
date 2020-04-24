import os

import configurations.importer
from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'dandi.settings'
if not os.environ.get('DANDI_CONFIGURATION'):
    raise ValueError('The environment variable "DANDI_CONFIGURATION" must be set.')
configurations.importer.ConfigurationImporter.namevar = 'DANDI_CONFIGURATION'
configurations.importer.install()

application = get_wsgi_application()
