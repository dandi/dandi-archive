# ruff: noqa: I002
# NOTE: Do not add from __future import annotations here.
# For some reason that breaks django-ninja

from typing import Any, Literal
import uuid

from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from ninja import Field, ModelSchema, NinjaAPI, Query, Schema
from ninja.pagination import PageNumberPagination, paginate
from rest_framework.utils.urls import replace_query_param

from dandiapi.api.asset_paths import get_path_children
from dandiapi.api.models.asset import Asset
from dandiapi.api.models.asset_paths import AssetPath
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.version import Version


class DandiNinjaPagination(PageNumberPagination):
    items_attribute: str = 'results'

    class Input(Schema):
        page: int = 1
        page_size: int = 100

    class Output(Schema):
        count: int
        next: str | None
        prev: str | None
        results: list[Any]

    def paginate_queryset(
        self, queryset: QuerySet, pagination: Input, request: WSGIRequest, **params: Any
    ) -> Any:
        offset = (pagination.page - 1) * pagination.page_size
        count = queryset.count()

        url = request.build_absolute_uri()
        next_link = (
            replace_query_param(url, 'page', pagination.page + 1)
            if offset + pagination.page_size < count
            else None
        )
        prev_link = (
            replace_query_param(url, 'page', pagination.page - 1) if pagination.page > 1 else None
        )

        return {
            'count': count,
            'next': next_link,
            'prev': prev_link,
            'results': queryset[offset : offset + pagination.page_size],
        }


class PathQuerySchema(Schema):
    dandiset_id: str
    version_id: str
    path: str = ''
    metadata: bool = False
    children: bool = False


class PathAssetSchema(ModelSchema):
    class Meta:
        model = Asset
        fields = [
            'asset_id',
            'path',
            'created',
            'modified',
        ]

    # Define these fields manually, since they can't be pulled from the model directly
    zarr: uuid.UUID | None
    blob: uuid.UUID | None
    metadata: dict | None

    # No resolver is needed as it will access the asset property by default
    size: int

    @staticmethod
    def resolve_blob(obj: Asset):
        if obj.blob is None:
            return None

        return obj.blob.blob_id

    @staticmethod
    def resolve_zarr(obj: Asset):
        if obj.zarr is None:
            return None

        return obj.zarr.zarr_id

    @staticmethod
    def resolve_metadata(obj: Asset, context):
        if getattr(context['request'], 'include_metadata', False):
            return obj.metadata

        return None


class PathFolderSchema(ModelSchema):
    class Meta:
        model = AssetPath
        fields = ['path']

    path: str
    total_assets: int = Field(alias='aggregate_files')
    total_size: int = Field(alias='aggregate_size')


class PathResultsSchema(Schema):
    type: Literal['asset', 'folder']
    resource: PathAssetSchema | PathFolderSchema

    @staticmethod
    def resolve_type(obj: AssetPath):
        if obj.asset is not None:
            return 'asset'

        return 'folder'

    @staticmethod
    def resolve_resource(obj: AssetPath):
        if obj.asset is not None:
            return obj.asset

        return obj


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
    return qs.union(children_paths)


api = NinjaAPI()


@api.get('/assets/atpath', response=list[PathResultsSchema])
@paginate(DandiNinjaPagination)
def atpath(request, params: Query[PathQuerySchema]):
    dandiset = Dandiset.objects.get(id=int(params.dandiset_id))
    version = Version.objects.get(dandiset=dandiset, version=params.version_id)

    # Annotate request, so the schema can modify its behavior as needed
    request.include_metadata = params.metadata

    return get_atpath_queryset(version=version, path=params.path, children=params.children)
