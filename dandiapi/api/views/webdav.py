from __future__ import annotations

from typing import TYPE_CHECKING

from drf_yasg.utils import swagger_auto_schema
from rest_framework import pagination, serializers
from rest_framework.decorators import api_view

from dandiapi.api.asset_paths import get_path_children
from dandiapi.api.models.asset import Asset
from dandiapi.api.models.asset_paths import AssetPath
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.version import Version

if TYPE_CHECKING:
    from django.db.models import QuerySet


class PathFolderSerializer(serializers.ModelSerializer):
    path = serializers.CharField()
    total_assets = serializers.IntegerField(source='aggregate_files')
    total_size = serializers.IntegerField(source='aggregate_size')

    class Meta:
        model = AssetPath
        fields = [
            'path',
            'total_assets',
            'total_size',
        ]


class PathAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'asset_id',
            'path',
            'created',
            'modified',
            'zarr',
            'blob',
            'metadata',
            'size',
        ]

    blob = serializers.UUIDField(source='blob.blob_id', allow_null=True)
    zarr = serializers.UUIDField(source='zarr.zarr_id', allow_null=True)

    def __init__(self, *args, include_metadata=False, **kwargs):
        if not include_metadata:
            del self.fields['metadata']

        super().__init__(*args, **kwargs)


class PathResultSerializer(serializers.Serializer):
    type = serializers.SerializerMethodField()
    resource = serializers.SerializerMethodField()

    def get_type(self, obj: AssetPath):
        if obj.asset is not None:
            return 'asset'
        return 'folder'

    def get_resource(self, obj: AssetPath):
        if obj.asset is not None:
            return PathAssetSerializer(obj.asset, include_metadata=self.context['metadata']).data
        return PathFolderSerializer(obj).data


class AtPathQuerySerializer(serializers.Serializer):
    dandiset_id = serializers.CharField()
    version_id = serializers.CharField()
    path = serializers.CharField(default='')
    metadata = serializers.BooleanField(default=False)
    children = serializers.BooleanField(default=False)


def get_atpath_queryset(*, version: Version, path: str, children: bool) -> QuerySet[AssetPath]:
    select_related_clauses = ('asset', 'asset__blob')
    qs = AssetPath.objects.select_related(*select_related_clauses).filter(version=version)

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
    return qs.union(children_paths).order_by('path')


@swagger_auto_schema(
    query_serializer=AtPathQuerySerializer,
    responses={200: PathResultSerializer(many=True)},
    method='GET',
)
@api_view(['GET'])
def atpath(request):
    query_serializer = AtPathQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)

    params = query_serializer.validated_data
    dandiset = Dandiset.objects.get(id=int(params['dandiset_id']))
    version = Version.objects.get(dandiset=dandiset, version=params['version_id'])

    qs = get_atpath_queryset(version=version, path=params['path'], children=params['children'])

    paginator = pagination.PageNumberPagination()
    result_page = paginator.paginate_queryset(qs, request=request)
    serializer = PathResultSerializer(
        instance=result_page, many=True, context={'metadata': params['metadata']}
    )

    return paginator.get_paginated_response(serializer.data)
