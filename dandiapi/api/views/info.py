from django.conf import settings
from drf_yasg.utils import no_body, swagger_auto_schema
import requests
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

schema_url = (
    'https://raw.githubusercontent.com/dandi/schema/master/'
    f'releases/{settings.DANDI_SCHEMA_VERSION}/dandiset.json'
)


class ApiInfoSerializer(serializers.Serializer):
    schema_version = serializers.CharField()
    schema_url = serializers.URLField()
    tag = serializers.CharField()


@swagger_auto_schema(
    request_body=no_body,
    responses={200: ApiInfoSerializer},
    method='GET',
)
@api_view()
def info_view(self):
    # Right now the production deployment is tracking master, which makes tags basically useless.
    # TODO: Deploy from tags, and report that tag here.
    resp = requests.get('https://api.github.com/repos/dandi/dandi-api/releases')
    tags = [release['tag_name'] for release in resp.json()]
    tag = tags[0]

    serializer = ApiInfoSerializer(
        data={
            'schema_version': settings.DANDI_SCHEMA_VERSION,
            'schema_url': schema_url,
            'tag': tag,
        }
    )
    serializer.is_valid(raise_exception=True)

    return Response(serializer.validated_data)
