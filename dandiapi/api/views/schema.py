from __future__ import annotations

from typing import TYPE_CHECKING

from dandischema.models import Asset, Dandiset, PublishedAsset, PublishedDandiset
from dandischema.utils import TransitionalGenerateJsonSchema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

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
    model = serializers.ChoiceField(choices=list(_model_name_mapping))


@swagger_auto_schema(
    method='GET',
    operation_summary='Get model schema',
    operation_description='Returns the JSON Schema of the requested metadata model',
)
@api_view(['GET'])
def schema_view(request: Request) -> Response:
    """
    Return the JSON Schema of the requested metadata model.

    This endpoint returns the JSON Schema of the requested metadata model
    as it is defined in this DANDI archive instance, with instance specific
    parameters such as instance name and DOI prefix.
    """
    serializer = SchemaQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    # Generate the JSON schema using the same approach as dandischema
    model_class = _model_name_mapping[serializer.validated_data['model']]
    schema = model_class.model_json_schema(schema_generator=TransitionalGenerateJsonSchema)

    return Response(schema)
