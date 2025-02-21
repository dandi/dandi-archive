from __future__ import annotations

from typing import TYPE_CHECKING

from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view

from dandiapi.api.asset_paths import get_path_children
from dandiapi.api.models.asset_paths import AssetPath
from dandiapi.api.models.version import Version
from dandiapi.api.views.common import PAGINATION_PARAMS
from dandiapi.api.views.pagination import DandiPagination

from .serializers import AtPathQuerySerializer, PathResultSerializer

if TYPE_CHECKING:
    from django.db.models import QuerySet


def get_atpath_queryset(*, version: Version, path: str, children: bool) -> QuerySet[AssetPath]:
    select_related_clauses = ('asset', 'asset__blob')
    qs = (
        AssetPath.objects.select_related(*select_related_clauses)
        .filter(version=version)
        .order_by('path')
    )

    # Handle root path case explicitly
    if path == '':
        return qs.exclude(path__contains='/') if children else qs.none()

    # Perform path filter
    qs = qs.filter(path=path)

    # Ensure queryset isn't empty
    asset_path = qs.first()
    if asset_path is None:
        return qs.none()

    # Since path+version combinations are unique, we know we've matched exactly one path.
    # Now see if we should extend this with it's children
    if asset_path.asset is not None or not children:
        return qs

    # Now we know path is a folder, and we should show its children
    children_paths = (
        get_path_children(asset_path).select_related(None).select_related(*select_related_clauses)
    )

    # Must include an additional order clause here to ensure correct ordering
    return qs.union(children_paths).order_by('path')


@swagger_auto_schema(
    query_serializer=AtPathQuerySerializer,
    manual_parameters=PAGINATION_PARAMS,
    responses={200: PathResultSerializer(many=True)},
    method='GET',
)
@api_view(['GET'])
def atpath(request):
    query_serializer = AtPathQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)

    params = query_serializer.validated_data
    version = get_object_or_404(
        Version.objects.select_related('dandiset'),
        dandiset_id=int(params['dandiset_id']),
        version=params['version_id'],
    )

    qs = get_atpath_queryset(version=version, path=params['path'], children=params['children'])

    paginator = DandiPagination()
    result_page = paginator.paginate_queryset(qs, request=request)
    serializer = PathResultSerializer(
        instance=result_page, many=True, context={'metadata': params['metadata']}
    )

    return paginator.get_paginated_response(serializer.data)
