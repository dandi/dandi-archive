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


# The names are spelled out explicitly (rather than derived from `__name__`), since as of
# dandischema 0.13.0 (schema 0.8.0) `PublishedDandiset` and `PublishedAsset` are merely
# deprecated aliases of `Dandiset` and `Asset` (a record is "published" iff its `datePublished`
# is set). Keep accepting the `Published*` names so that existing API clients do not break.
# TODO: drop the `Published*` names once dandischema removes those aliases.
_model_name_mapping = {
    'Dandiset': Dandiset,
    'Asset': Asset,
    'PublishedDandiset': PublishedDandiset,
    'PublishedAsset': PublishedAsset,
}


class SchemaQuerySerializer(serializers.Serializer):
    model = serializers.ChoiceField(choices=list(_model_name_mapping))


@swagger_auto_schema(method='GET', operation_summary='List schema models')
@api_view(['GET'])
def schema_list_view(request: Request) -> Response:
    """Return the list of models which can be requested via the schema endpoint."""
    return Response(_model_name_mapping.keys())


@swagger_auto_schema(
    method='GET',
    operation_summary='Get model schema',
    operation_description='Returns the JSON Schema of the requested metadata model',
    query_serializer=SchemaQuerySerializer,
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
