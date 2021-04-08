from pathlib import Path
from typing import Type

from composed_configuration import (
    ComposedConfiguration,
    ConfigMixin,
    DevelopmentBaseConfiguration,
    HerokuProductionBaseConfiguration,
    ProductionBaseConfiguration,
    TestingBaseConfiguration,
)
from configurations import values


class DandiMixin(ConfigMixin):
    WSGI_APPLICATION = 'dandiapi.wsgi.application'
    ROOT_URLCONF = 'dandiapi.urls'

    BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

    REST_FRAMEWORK_EXTENSIONS = {'DEFAULT_PARENT_LOOKUP_KWARG_NAME_PREFIX': ''}

    ACCOUNT_EMAIL_VERIFICATION = 'none'

    @staticmethod
    def before_binding(configuration: Type[ComposedConfiguration]):
        # Install local apps first, to ensure any overridden resources are found first
        configuration.INSTALLED_APPS = [
            'dandiapi.api.apps.PublishConfig',
        ] + configuration.INSTALLED_APPS

        # Install additional apps
        configuration.INSTALLED_APPS += [
            'guardian',
            'allauth.socialaccount.providers.github',
        ]

        configuration.AUTHENTICATION_BACKENDS += ['guardian.backends.ObjectPermissionBackend']
        configuration.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += [
            # TODO remove TokenAuthentication, it is only here to support
            # the setTokenHack login workaround
            'rest_framework.authentication.TokenAuthentication',
        ]
        configuration.REST_FRAMEWORK[
            'DEFAULT_PAGINATION_CLASS'
        ] = 'dandiapi.api.views.common.DandiPagination'

    DANDI_DANDISETS_BUCKET_NAME = values.Value(environ_required=True)
    DANDI_DANDISETS_BUCKET_PREFIX = values.Value(default='', environ=True)
    DANDI_GIRDER_API_URL = values.URLValue(environ_required=True)
    DANDI_GIRDER_API_KEY = values.Value(environ_required=True)
    DANDI_SCHEMA_VERSION = values.Value(environ_required=True)

    DANDI_DOI_API_URL = values.URLValue(environ=True)
    DANDI_DOI_API_USER = values.Value(environ=True)
    DANDI_DOI_API_PASSWORD = values.Value(environ=True)
    DANDI_DOI_API_PREFIX = values.Value(environ=True)

    # The CloudAMQP connection was dying, using the heartbeat should keep it alive
    CELERY_BROKER_HEARTBEAT = 20


class DevelopmentConfiguration(DandiMixin, DevelopmentBaseConfiguration):
    pass


class TestingConfiguration(DandiMixin, TestingBaseConfiguration):
    MINIO_STORAGE_MEDIA_BUCKET_NAME = 'test-django-storage'
    MINIO_STORAGE_MEDIA_URL = 'http://localhost:9000/test-django-storage'

    DANDI_DANDISETS_BUCKET_NAME = 'test-dandiapi-dandisets'
    DANDI_GIRDER_API_KEY = 'testkey'
    DANDI_GIRDER_API_URL = 'http://girder.test/api/v1'


class ProductionConfiguration(DandiMixin, ProductionBaseConfiguration):
    pass


class HerokuProductionConfiguration(DandiMixin, HerokuProductionBaseConfiguration):
    # All login attempts in production should go straight to GitHub
    LOGIN_URL = '/accounts/github/login/'
