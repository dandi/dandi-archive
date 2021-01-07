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
        configuration.INSTALLED_APPS += [
            'dandiapi.api.apps.PublishConfig',
            'guardian',
            'allauth.socialaccount.providers.github',
        ]
        configuration.AUTHENTICATION_BACKENDS += ['guardian.backends.ObjectPermissionBackend']
        configuration.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += [
            # Required for swagger logins
            'rest_framework.authentication.SessionAuthentication',
            # TODO remove TokenAuthentication, it is only here to support
            # the setTokenHack login workaround
            'rest_framework.authentication.TokenAuthentication',
        ]
        configuration.REST_FRAMEWORK[
            'DEFAULT_PAGINATION_CLASS'
        ] = 'dandiapi.api.views.common.DandiPagination'

    DANDI_DANDISETS_BUCKET_NAME = values.Value(environ_required=True)
    DANDI_GIRDER_API_URL = values.URLValue(environ_required=True)
    DANDI_GIRDER_API_KEY = values.Value(environ_required=True)


class DevelopmentConfiguration(DandiMixin, DevelopmentBaseConfiguration):
    pass


class TestingConfiguration(DandiMixin, TestingBaseConfiguration):
    MINIO_STORAGE_MEDIA_BUCKET_NAME = 'test-django-storage'

    DANDI_DANDISETS_BUCKET_NAME = 'test-dandiapi-dandisets'
    DANDI_GIRDER_API_KEY = 'testkey'
    DANDI_GIRDER_API_URL = 'http://girder.test/api/v1'


class ProductionConfiguration(DandiMixin, ProductionBaseConfiguration):
    pass


class HerokuProductionConfiguration(DandiMixin, HerokuProductionBaseConfiguration):
    pass
