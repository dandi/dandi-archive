import logging
from pathlib import Path
from typing import Type

from configurations import values
from django_girders.configuration import (
    ComposedConfiguration,
    ConfigMixin,
    DevelopmentBaseConfiguration,
    HerokuProductionBaseConfiguration,
    ProductionBaseConfiguration,
    TestingBaseConfiguration,
)


class SentryConfig(ConfigMixin):
    SENTRY_DSN = values.Value(environ_required=True)

    @staticmethod
    def after_binding(configuration: Type[ComposedConfiguration]) -> None:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=configuration.SENTRY_DSN,
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.WARNING),
            ],
            send_default_pii=True,
        )


class DandiConfig(ConfigMixin):
    WSGI_APPLICATION = 'dandi.wsgi.application'
    ROOT_URLCONF = 'dandi.urls'

    BASE_DIR = str(Path(__file__).absolute().parent.parent)

    REST_FRAMEWORK_EXTENSIONS = {'DEFAULT_PARENT_LOOKUP_KWARG_NAME_PREFIX': ''}

    @staticmethod
    def before_binding(configuration: Type[ComposedConfiguration]):
        configuration.INSTALLED_APPS += ['publish.apps.PublishConfig']

    DANDI_DANDISETS_BUCKET_NAME = values.Value(environ_required=True)
    DANDI_GIRDER_API_URL = values.URLValue(environ_required=True)
    DANDI_GIRDER_API_KEY = values.Value(environ_required=True)


class DevelopmentConfiguration(DandiConfig, DevelopmentBaseConfiguration):
    pass


class TestingConfiguration(DandiConfig, TestingBaseConfiguration):
    MINIO_STORAGE_MEDIA_BUCKET_NAME = 'test-django-storage'

    DANDI_DANDISETS_BUCKET_NAME = 'test-dandi-dandisets'
    DANDI_GIRDER_API_KEY = 'testkey'
    DANDI_GIRDER_API_URL = 'http://localhost:8080/'


class ProductionConfiguration(DandiConfig, SentryConfig, ProductionBaseConfiguration):
    pass


class HerokuProductionConfiguration(DandiConfig, SentryConfig, HerokuProductionBaseConfiguration):
    pass
