from __future__ import annotations

from dandischema.conf import get_instance_config
from django.conf import settings
from django.urls import reverse
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from dandiapi import __version__

_INSTANCE_CONFIG = get_instance_config()


def get_schema_url(request):
    """Get the URL for the schema based on current server deployment."""
    # Use the local schema endpoint instead of GitHub
    return request.build_absolute_uri(reverse('schema-dandiset-latest'))


class ApiServiceSerializer(serializers.Serializer):
    url = serializers.CharField()


class ApiServicesSerializer(serializers.Serializer):
    api = ApiServiceSerializer()
    webui = ApiServiceSerializer()
    jupyterhub = ApiServiceSerializer()


class ApiInfoSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Need to add fields here to allow for hyphens in name.
        # dandi-cli expects these exact field names (with hyphens), so
        # these fields must remain unchanged.
        self.fields.update(
            {
                'cli-minimal-version': serializers.CharField(),
                'cli-bad-versions': serializers.ListField(child=serializers.CharField()),
            }
        )

    # Instance Configuration
    instance_config = serializers.JSONField()

    # Schema
    schema_version = serializers.CharField()
    schema_url = serializers.URLField()

    # Versions
    version = serializers.CharField()

    # Services
    services = ApiServicesSerializer()


@swagger_auto_schema(
    request_body=no_body,
    responses={200: ApiInfoSerializer},
    method='GET',
)
@api_view()
def info_view(request):
    api_url = f'{settings.DANDI_API_URL}/api'
    serializer = ApiInfoSerializer(
        data={
            'instance_config': _INSTANCE_CONFIG.model_dump(
                # Not excluding any `None` values in this object because the `None` values are
                # needed to set the instance configuration in dandi-cli properly since
                # a corresponding environment variable is used to set the instance configuration if
                # the argument for a particular field is not provided.
                mode='json'
            ),
            'schema_version': settings.DANDI_SCHEMA_VERSION,
            'schema_url': get_schema_url(request),
            'version': __version__,
            'cli-minimal-version': '0.60.0',
            'cli-bad-versions': [],
            'services': {
                'api': {'url': api_url},
                'webui': {'url': settings.DANDI_WEB_APP_URL},
                'jupyterhub': {'url': settings.DANDI_JUPYTERHUB_URL},
            },
        }
    )
    serializer.is_valid(raise_exception=True)

    return Response(serializer.validated_data)
