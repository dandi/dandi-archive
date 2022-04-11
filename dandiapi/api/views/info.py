from django.conf import settings
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

import versioneer

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
    # Schema
    schema_version = serializers.CharField()
    schema_url = serializers.URLField()

    # Versions
    version = serializers.CharField()
    cli_minimal_version = serializers.CharField()
    cli_bad_versions = serializers.ListField(child=serializers.CharField())

    # Services
    services = ApiServicesSerializer()


@swagger_auto_schema(
    request_body=no_body,
    responses={200: ApiInfoSerializer},
    method='GET',
)
@api_view()
def info_view(self):
    serializer = ApiInfoSerializer(
        data={
            'schema_version': settings.DANDI_SCHEMA_VERSION,
            'schema_url': schema_url,
            # TODO: Use git describe --abbrev=0
            'version': versioneer.get_version(),
            # TODO: Determine what these should be
            "cli_minimal_version": "0.14.2",
            "cli_bad_versions": [],
            "services": {
                "api": {"url": settings.DANDI_API_URL},
                "webui": {"url": settings.DANDI_WEB_APP_URL},
                # TODO: Add jupyter hub api setting
                "jupyterhub": {"url": "https://hub.dandiarchive.org"},
            },
        }
    )
    serializer.is_valid(raise_exception=True)

    return Response(serializer.validated_data)
