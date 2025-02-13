# ruff: noqa: TC003

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Literal
import uuid

from ninja import NinjaAPI, Query, Schema
from ninja.pagination import PageNumberPagination, paginate

from dandiapi.api.models.asset_paths import AssetPath
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.version import Version

if TYPE_CHECKING:
    from dandiapi.api.models.asset import Asset


class AtPathQuerySchema(Schema):
    dandiset_id: str
    version_id: str
    path: str = ''
    metadata: bool = False
    children: bool = False


class AtPathAssetSchema(Schema):
    asset_id: uuid.UUID
    blob: uuid.UUID | None
    zarr: uuid.UUID | None
    path: str
    size: int
    created: datetime.datetime
    modified: datetime.datetime
    metadata: dict | None

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
    def resolve_metadata(obj: Asset):
        if getattr(obj, '_include_metadata', False):
            return obj.metadata

        return None


class AtPathFolderSchema(Schema):
    path: str
    total_assets: int
    total_size: int


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

        return AtPathFolderSchema(
            path=obj.path, total_assets=obj.aggregate_files, total_size=obj.aggregate_size
        )


api = NinjaAPI()


@api.get('/assets/atpath', response=list[AtPathResultsSchema])
@paginate(PageNumberPagination)
def atpath(
    request,
    params: Query[AtPathQuerySchema],
    # dandiset_id: str,
    # version_id: str,
    # path: str = '',
    # metadata: bool = False,
    # children: bool = False,
):
    dandiset = Dandiset.objects.get(id=int(params.dandiset_id))
    version = Version.objects.get(dandiset=dandiset, version=params.version_id)

    # Check if path is an asset
    qs = AssetPath.objects.select_related('asset').filter(version=version)
    qs = qs.exclude(path__contains='/') if params.path == '' else qs.filter(path=params.path)

    count = qs.count()
    if count > 1:
        return qs

    res = qs.first()
    if res is None:
        return []

    return [res]
