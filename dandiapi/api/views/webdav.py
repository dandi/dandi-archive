# ruff: noqa: I002
# NOTE: Do not add from __future import annotations here.
# For some reason that breaks django-ninja

from typing import Literal
import uuid

from ninja import Field, ModelSchema, NinjaAPI, Query, Schema
from ninja.pagination import PageNumberPagination, paginate
from ninja.renderers import JSONRenderer

from dandiapi.api.asset_paths import get_path_children
from dandiapi.api.models.asset import Asset
from dandiapi.api.models.asset_paths import AssetPath
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.version import Version


class AtPathQuerySchema(Schema):
    dandiset_id: str
    version_id: str
    path: str = ''
    metadata: bool = False
    children: bool = False


class AtPathAssetSchema(ModelSchema):
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


class AtPathFolderSchema(Schema):
    path: str
    total_assets: int = Field(alias='aggregate_files')
    total_size: int = Field(alias='aggregate_size')


class AtPathResultsSchema(Schema):
    type: Literal['asset', 'folder']
    resource: AtPathAssetSchema | AtPathFolderSchema

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


api = NinjaAPI()


@api.get('/assets/atpath', response=list[AtPathResultsSchema])
@paginate(PageNumberPagination)
def atpath(request, params: Query[AtPathQuerySchema]):
    dandiset = Dandiset.objects.get(id=int(params.dandiset_id))
    version = Version.objects.get(dandiset=dandiset, version=params.version_id)

    # Annotate request, so the schema can modify its behavior as needed
    request.include_metadata = params.metadata

    # Base query
    select_related_clauses = ('asset', 'asset__blob')
    qs = AssetPath.objects.select_related(*select_related_clauses).filter(version=version)

    # Handle root path case explicitly
    if params.path == '':
        return qs.exclude(path__contains='/') if params.children else qs.none()

    # Perform path filter
    qs = qs.filter(path=params.path)

    # Ensure queryset isn't empty
    path = qs.first()
    if path is None:
        return []

    # Since path+version combinations are unique, we know we've matched exactly one path.
    # Now see if we should extend this with it's children
    if path.asset is not None or not params.children:
        return [path]

    # Now we know path is a folder, and we should show its children
    children = get_path_children(path).select_related(None).select_related(*select_related_clauses)
    return qs.union(children).order_by('path')
