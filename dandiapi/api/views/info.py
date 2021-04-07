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


class ApiInfoSerializer(serializers.Serializer):
    schema_version = serializers.CharField()
    schema_url = serializers.URLField()
    version = serializers.CharField()


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
            'version': versioneer.get_version(),
        }
    )
    serializer.is_valid(raise_exception=True)

    return Response(serializer.validated_data)
