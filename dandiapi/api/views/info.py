import os

from django.conf import settings
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from dandiapi import __version__

schema_url = (
    'https://raw.githubusercontent.com/dandi/schema/master/'
    f'releases/{settings.DANDI_SCHEMA_VERSION}/dandiset.json'
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
def info_view(self):
    api_url = os.path.join(settings.DANDI_API_URL, 'api')
    serializer = ApiInfoSerializer(
        data={
            'schema_version': settings.DANDI_SCHEMA_VERSION,
            'schema_url': schema_url,
            'version': __version__,
            'cli-minimal-version': '0.51.0',
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
