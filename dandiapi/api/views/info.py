from __future__ import annotations

import importlib.metadata
from urllib.parse import ParseResult, urlencode, urlparse, urlunparse

from dandischema.conf import get_instance_config
from dandischema.consts import ALLOWED_INPUT_SCHEMAS, DANDI_SCHEMA_VERSION
from django.conf import settings
from django.urls import reverse
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response


def get_schema_url():
    """Get the URL for the schema based on current server deployment."""
    scheme, netloc = urlparse(settings.DANDI_API_URL)[:2]
    return urlunparse(
        ParseResult(
            scheme=scheme,
            netloc=netloc,
            path=reverse('schema-view'),
            query=urlencode({'model': 'Dandiset'}),
            params='',
            fragment='',
        )
    )


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
    allowed_schema_versions = serializers.ListField(child=serializers.CharField())

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
            # Set exclude_none=False to prevent any fields set to `None` from being set to a
            # different default value when the JSON is de-serialized into a Pydantic model.
            'instance_config': get_instance_config().model_dump(mode='json', exclude_none=False),
            'schema_version': DANDI_SCHEMA_VERSION,
            'schema_url': get_schema_url(),
            'allowed_schema_versions': ALLOWED_INPUT_SCHEMAS,
            'version': importlib.metadata.version('dandiapi'),
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
