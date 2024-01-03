from __future__ import annotations
import os

import configurations.importer
from django.core.asgi import get_asgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'dandiapi.settings'
if not os.environ.get('DJANGO_CONFIGURATION'):
    raise ValueError('The environment variable "DJANGO_CONFIGURATION" must be set.')
configurations.importer.install()

application = get_asgi_application()
