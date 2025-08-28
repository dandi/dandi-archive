from __future__ import annotations

from typing import TYPE_CHECKING

from dandischema.models import Asset, Dandiset, PublishedAsset, PublishedDandiset
from dandischema.utils import TransitionalGenerateJsonSchema
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from dandiapi.api.services.exceptions import DandiError

if TYPE_CHECKING:
    from rest_framework.request import Request


_model_name_mapping = {
    m.__name__: m
    for m in [
        Dandiset,
        Asset,
        PublishedDandiset,
        PublishedAsset,
    ]
}


class SchemaQuerySerializer(serializers.Serializer):
    version = serializers.CharField(default='latest')
    model = serializers.ChoiceField(choices=list(_model_name_mapping))


@swagger_auto_schema(
    method='GET',
    operation_summary='Get model schemas',
    operation_description='Returns the JSONSchema for supplied model metadata',
)
@api_view(['GET'])
def schema_view(request: Request, version: str | None = None) -> Response:
    """
    Return the JSONSchema for Dandiset metadata.

    This endpoint provides the currently configured schema based on the application's
    DANDI_SCHEMA_VERSION setting. It can be used as a replacement for the static
    schema files hosted on GitHub.

    If a version is provided and does not match the current version, a 404 is returned.
    In the future, multiple versions could be supported.
    """
    serializer = SchemaQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    version = serializer.validated_data['version']
    if version and version not in {settings.DANDI_SCHEMA_VERSION, 'latest'}:
        raise DandiError(
            message=f'Invalid schema version {version}.'
            f' Server schema version is {settings.DANDI_SCHEMA_VERSION}',
            http_status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Generate the schema JSON using the same approach as dandischema
    model_class = _model_name_mapping[serializer.validated_data['model']]
    schema = model_class.model_json_schema(schema_generator=TransitionalGenerateJsonSchema)

    return Response(schema)
