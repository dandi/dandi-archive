import os
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

    DANDI_ALLOW_LOCALHOST_URLS = False

    @staticmethod
    def mutate_configuration(configuration: Type[ComposedConfiguration]):
        # Install local apps first, to ensure any overridden resources are found first
        configuration.INSTALLED_APPS = [
            'dandiapi.api.apps.PublishConfig',
        ] + configuration.INSTALLED_APPS

        # Install additional apps
        configuration.INSTALLED_APPS += [
            'guardian',
            'allauth.socialaccount.providers.github',
        ]

        # Authentication
        configuration.AUTHENTICATION_BACKENDS += ['guardian.backends.ObjectPermissionBackend']
        configuration.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += [
            # TODO remove TokenAuthentication, it is only here to support
            # the setTokenHack login workaround
            'rest_framework.authentication.TokenAuthentication',
        ]

        # Permission
        configuration.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] += [
            'dandiapi.api.permissions.IsApprovedOrReadOnly'
        ]

        # Pagination
        configuration.REST_FRAMEWORK[
            'DEFAULT_PAGINATION_CLASS'
        ] = 'dandiapi.api.views.common.DandiPagination'

        # If this environment variable is set, the pydantic model will allow URLs with localhost
        # in them. This is important for development and testing environments, where URLs will
        # frequently point to localhost.
        if configuration.DANDI_ALLOW_LOCALHOST_URLS:
            os.environ['DANDI_ALLOW_LOCALHOST_URLS'] = 'True'

    DANDI_DANDISETS_BUCKET_NAME = values.Value(environ_required=True)
    DANDI_DANDISETS_BUCKET_PREFIX = values.Value(default='', environ=True)
    DANDI_DANDISETS_EMBARGO_BUCKET_NAME = values.Value(environ_required=True)
    DANDI_DANDISETS_EMBARGO_BUCKET_PREFIX = values.Value(default='', environ=True)
    DANDI_ZARR_PREFIX_NAME = values.Value(default='zarr', environ=True)
    DANDI_ZARR_CHECKSUM_PREFIX_NAME = values.Value(default='zarr-checksums', environ=True)

    # Mainly applies to unembargo
    DANDI_MULTIPART_COPY_MAX_WORKERS = values.IntegerValue(environ=True, default=50)

    # This is where the schema version should be set.
    # It can optionally be overwritten with the environment variable, but that should only be
    # considered a temporary fix.
    DANDI_SCHEMA_VERSION = values.Value(default='0.6.2', environ=True)

    DANDI_DOI_API_URL = values.URLValue(environ=True)
    DANDI_DOI_API_USER = values.Value(environ=True)
    DANDI_DOI_API_PASSWORD = values.Value(environ=True)
    DANDI_DOI_API_PREFIX = values.Value(environ=True)
    DANDI_DOI_PUBLISH = values.BooleanValue(environ=True, default=False)
    DANDI_WEB_APP_URL = values.URLValue(environ_required=True)
    DANDI_API_URL = values.URLValue(environ_required=True)

    DANDI_VALIDATION_JOB_INTERVAL = values.IntegerValue(environ=True, default=60)

    # The CloudAMQP connection was dying, using the heartbeat should keep it alive
    CELERY_BROKER_HEARTBEAT = 20

    # Clearing out the stock `SWAGGER_SETTINGS` variable causes a Django login
    # button to appear in Swagger, along with a spurious "authorize" button that
    # doesn't work. This at least enables us to authorize to the Swagger page on
    # the spot, which is quite useful.
    #
    # When Brian Helba is able to resolve this problem upstream (in
    # django-composed-configuration) we can remove this setting.
    SWAGGER_SETTINGS = {
        'DEFAULT_AUTO_SCHEMA_CLASS': 'dandiapi.swagger.DANDISwaggerAutoSchema',
    }

    # Some tasks working with lots of data need lots of memory, so we need to artificially lower
    # the number of concurrent tasks (default is 8) to keep memory usage down.
    CELERY_WORKER_CONCURRENCY = values.IntegerValue(environ=True, default=8)

    # Automatically approve new users by default
    AUTO_APPROVE_USERS = True


class DevelopmentConfiguration(DandiMixin, DevelopmentBaseConfiguration):
    # This makes pydantic model schema allow URLs with localhost in them.
    DANDI_ALLOW_LOCALHOST_URLS = True


class TestingConfiguration(DandiMixin, TestingBaseConfiguration):
    DANDI_DANDISETS_BUCKET_NAME = 'test-dandiapi-dandisets'
    DANDI_DANDISETS_BUCKET_PREFIX = 'test-prefix/'
    DANDI_DANDISETS_EMBARGO_BUCKET_NAME = 'test--embargo-dandiapi-dandisets'
    DANDI_DANDISETS_EMBARGO_BUCKET_PREFIX = 'test-embargo-prefix/'
    DANDI_ZARR_PREFIX_NAME = 'test-zarr'
    DANDI_ZARR_CHECKSUM_PREFIX_NAME = 'test-zarr-checksums'

    # This makes the dandischema pydantic model allow URLs with localhost in them.
    DANDI_ALLOW_LOCALHOST_URLS = True

    # Ensure celery tasks run synchronously
    CELERY_TASK_ALWAYS_EAGER = True


class ProductionConfiguration(DandiMixin, ProductionBaseConfiguration):
    pass


class HerokuProductionConfiguration(DandiMixin, HerokuProductionBaseConfiguration):
    # All login attempts in production should go straight to GitHub
    LOGIN_URL = '/accounts/github/login/'

    # Don't require a POST request to initiate a GitHub login
    # https://github.com/pennersr/django-allauth/blob/HEAD/ChangeLog.rst#backwards-incompatible-changes-2
    SOCIALACCOUNT_LOGIN_ON_GET = True

    # Don't automatically approve users in production. Instead they must be
    # manually approved by an admin.
    AUTO_APPROVE_USERS = False


# NOTE: The staging configuration uses a custom OAuth toolkit `Application` model
# (`StagingApplication`) to allow for wildcards in OAuth redirect URIs (to support Netlify branch
# deploy previews, etc). Note that both the custom `StagingApplication` and default
# `oauth2_provider.models.Application` will have Django database models and will show up on the
# Django admin, but only one of them will be in active use depending on the environment
# the API server is running in (production/local or staging).
class HerokuStagingConfiguration(HerokuProductionConfiguration):
    OAUTH2_PROVIDER_APPLICATION_MODEL = 'api.StagingApplication'
