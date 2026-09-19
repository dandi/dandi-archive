from __future__ import annotations

import re
from typing import TYPE_CHECKING

from dandischema.consts import DANDI_SCHEMA_VERSION
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from dandiapi.api.asset_paths import search_asset_paths
from dandiapi.api.models import Asset, AssetBlob, Version
from dandiapi.api.models.asset import validate_asset_path
from dandiapi.api.services.asset import (
    add_asset_to_version,
    bulk_remove_assets_from_version,
    change_asset,
)
from dandiapi.api.services.asset.exceptions import DraftDandisetNotModifiableError
from dandiapi.api.services.embargo.exceptions import DandisetUnembargoInProgressError
from dandiapi.api.services.permissions.dandiset import (
    is_owned_asset,
    require_dandiset_owner_or_403,
)
from dandiapi.api.views.common import (
    ASSET_ID_PARAM,
    PAGINATION_PARAMS,
    VERSIONS_DANDISET_PK_PARAM,
    VERSIONS_VERSION_PARAM,
)
from dandiapi.api.views.pagination import DandiPagination, LazyPagination
from dandiapi.api.views.serializers import (
    AssetBulkDeleteRequestSerializer,
    AssetDetailSerializer,
    AssetDownloadQueryParameterSerializer,
    AssetListSerializer,
    AssetPathsQueryParameterSerializer,
    AssetPathsSerializer,
    AssetSerializer,
    AssetValidationSerializer,
)
from dandiapi.api.views.version import get_readable_version_or_404
from dandiapi.zarr.models import ZarrArchive

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from rest_framework.request import Request


class AssetRequestSerializer(serializers.Serializer):
    metadata = serializers.JSONField()
    blob_id = serializers.UUIDField(required=False)
    zarr_id = serializers.UUIDField(required=False)

    def get_blob(self) -> AssetBlob | None:
        asset_blob = None
        if 'blob_id' in self.validated_data:
            asset_blob = get_object_or_404(AssetBlob, blob_id=self.validated_data['blob_id'])

        return asset_blob

    def get_zarr_archive(self) -> ZarrArchive | None:
        zarr_archive = None
        if 'zarr_id' in self.validated_data:
            zarr_archive = get_object_or_404(ZarrArchive, zarr_id=self.validated_data['zarr_id'])

        return zarr_archive

    def validate(self, data):
        """Ensure blob_id and zarr_id are mutually exclusive."""
        if ('blob_id' in data) == ('zarr_id' in data):
            raise serializers.ValidationError(
                {'blob_id': 'Exactly one of blob_id or zarr_id must be specified.'}
            )
        if 'path' not in data['metadata'] or not data['metadata']['path']:
            raise serializers.ValidationError({'metadata': 'No path specified in metadata.'})

        # Validate the asset path. If this fails, it will raise a django ValidationError, which
        # will be caught further up the stack and be converted to a DRF ValidationError
        validate_asset_path(data['metadata']['path'])

        data['metadata'].setdefault('schemaVersion', DANDI_SCHEMA_VERSION)
        return data


def get_readable_asset_or_404(request: Request, asset_id: str) -> Asset:
    """
    Fetch an asset by ID, ensuring the requesting user is permitted to read it.

    Embargoed assets are only readable by admins, and by owners of a dandiset that the
    asset belongs to.
    """
    # Select the blob and zarr, as both authorization and serialization need them
    asset = get_object_or_404(Asset.objects.select_related('blob', 'zarr'), asset_id=asset_id)
    if not asset.is_embargoed:
        return asset

    # Clients must be authenticated to access it
    if not request.user.is_authenticated:
        raise NotAuthenticated

    # Admins are allowed to access any embargoed asset
    if request.user.is_superuser:
        return asset

    # The user must be an owner of one of the dandisets this asset belongs to
    if not is_owned_asset(asset, request.user):
        raise PermissionDenied

    return asset


def _filter_assets(assets: QuerySet[Asset], *, path: str, order: list[str]) -> QuerySet[Asset]:
    """Apply the filtering and ordering requested by the asset list query parameters."""
    if path:
        assets = assets.filter(path__istartswith=path)
    if order:
        assets = assets.order_by(*order)

    return assets


def _asset_download_response(request: Request, asset: Asset) -> HttpResponse:
    """Redirect to the object store URL that the given asset can be downloaded from."""
    # Raise error if zarr
    if asset.zarr is not None:
        return Response(
            'Unable to provide download link for zarr assets.'
            ' Please browse the zarr files directly to do so.',
            status=status.HTTP_400_BAD_REQUEST,
        )

    asset_blob = asset.blob

    # Redirect to correct presigned URL
    serializer = AssetDownloadQueryParameterSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    content_disposition = serializer.validated_data['content_disposition']
    content_type = asset.metadata.get('encodingFormat', 'application/octet-stream')
    asset_basename = asset.path.split('/')[-1]

    if content_disposition == 'attachment':
        return HttpResponseRedirect(
            asset_blob.blob.storage.url(
                asset_blob.blob.name,
                parameters={
                    'ResponseContentDisposition': f'attachment; filename="{asset_basename}"',
                },
            )
        )
    if content_disposition == 'inline':
        url = asset_blob.blob.storage.url(
            asset_blob.blob.name,
            parameters={
                'ResponseContentDisposition': f'inline; filename="{asset_basename}"',
                'ResponseContentType': content_type,
            },
        )

        if content_type.startswith('video/'):
            return HttpResponse(
                f"""
                <video autoplay muted controls>
                    <source src="{url}">
                </video>
            """,
                content_type='text/html',
            )

        return HttpResponseRedirect(url)
    raise TypeError('Invalid content_disposition: %s', content_disposition)


@swagger_auto_schema(
    method='GET',
    manual_parameters=[ASSET_ID_PARAM],
    responses={
        200: 'The asset metadata.',
    },
    operation_summary="Get an asset's metadata",
)
@api_view(['GET', 'HEAD'])
def asset_view(request: Request, asset_id: str) -> Response:
    asset = get_readable_asset_or_404(request, asset_id)
    return Response(asset.full_metadata)


@swagger_auto_schema(
    method='GET',
    operation_id='assets_download',
    operation_summary='Get the download link for an asset.',
    operation_description='',
    manual_parameters=[ASSET_ID_PARAM],
    query_serializer=AssetDownloadQueryParameterSerializer,
    responses={
        200: None,  # This disables the auto-generated 200 response
        301: 'Redirect to object store',
    },
)
@api_view(['GET', 'HEAD'])
def asset_download_view(request: Request, asset_id: str) -> HttpResponse:
    asset = get_readable_asset_or_404(request, asset_id)
    return _asset_download_response(request, asset)


@swagger_auto_schema(
    method='GET',
    operation_id='assets_info',
    operation_summary='Django serialization of an asset',
    manual_parameters=[ASSET_ID_PARAM],
    responses={200: AssetDetailSerializer},
)
@api_view(['GET', 'HEAD'])
def asset_info_view(request: Request, asset_id: str) -> Response:
    asset = get_readable_asset_or_404(request, asset_id)
    serializer = AssetDetailSerializer(instance=asset)
    return Response(serializer.data, status=status.HTTP_200_OK)


def _list_version_assets(
    request: Request, versions__dandiset__pk: str, versions__version: str
) -> Response:
    version = get_readable_version_or_404(
        request, dandiset_pk=versions__dandiset__pk, version=versions__version
    )

    query_serializer = AssetListSerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)
    query = query_serializer.validated_data
    path: str = query.get('path', '')
    order: list[str] = query['order']

    # Use custom pagination class to reduce unnecessary counts of assets
    paginator = LazyPagination()

    asset_queryset = _filter_assets(version.assets.all(), path=path, order=order)

    # Check if the path query arg is pointing at a direct path.
    # If that's the case, just retrieve the single asset.
    if path:
        assets = Asset.objects.filter(path=path, versions=version)
        if assets.exists():
            asset_queryset = assets

    # Filter query to only zarr assets, if requested
    if query['zarr']:
        asset_queryset = asset_queryset.filter(zarr__isnull=False)

    # Must do glob pattern matching before pagination
    glob_pattern: str | None = query.get('glob')
    if glob_pattern is not None:
        # Escape special characters in the glob pattern. This is a security precaution taken
        # since we are using postgres' regex search. A malicious user who knows this could
        # include a regex as part of the glob expression, which postgres would happily parse
        # and use if it's not escaped.
        glob_pattern = f'^{re.escape(glob_pattern)}$'
        asset_queryset = asset_queryset.filter(path__iregex=glob_pattern.replace('\\*', '.*'))

    # Retrieve just the first N asset IDs, and use them for pagination
    page_of_asset_ids = paginator.paginate_queryset(
        asset_queryset.values_list('id', flat=True), request=request
    )

    # Now we can retrieve the actual fully joined rows using the limited number of assets we're
    # going to return
    queryset = _filter_assets(
        Asset.objects.filter(id__in=page_of_asset_ids).select_related('blob', 'zarr'),
        path=path,
        order=order,
    )

    # Must apply this to the main queryset, since it affects the data returned
    include_metadata = query['metadata']
    if not include_metadata:
        queryset = queryset.defer('metadata')

    # Paginate and return
    serializer = AssetSerializer(queryset, many=True, metadata=include_metadata)
    return paginator.get_paginated_response(serializer.data)


@require_dandiset_owner_or_403('versions__dandiset__pk')
def _create_version_asset(
    request: Request, versions__dandiset__pk: str, versions__version: str
) -> Response:
    version: Version = get_object_or_404(
        Version.objects.select_related('dandiset'),
        dandiset__pk=versions__dandiset__pk,
        version=versions__version,
    )

    if version.dandiset.unembargo_in_progress:
        raise DandisetUnembargoInProgressError

    serializer = AssetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    asset = add_asset_to_version(
        user=request.user,
        version=version,
        asset_blob=serializer.get_blob(),
        zarr_archive=serializer.get_zarr_archive(),
        metadata=serializer.validated_data['metadata'],
    )

    return Response(AssetDetailSerializer(instance=asset).data, status=status.HTTP_200_OK)


@require_dandiset_owner_or_403('versions__dandiset__pk')
def _bulk_delete_version_assets(
    request: Request, versions__dandiset__pk: str, versions__version: str
) -> Response:
    version = get_object_or_404(
        Version.objects.select_related('dandiset'),
        dandiset__pk=versions__dandiset__pk,
        version=versions__version,
    )
    if version.dandiset.unembargo_in_progress:
        raise DandisetUnembargoInProgressError

    serializer = AssetBulkDeleteRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    bulk_remove_assets_from_version(
        user=request.user,
        version=version,
        asset_ids=serializer.validated_data['asset_ids'],
    )

    return Response(None, status=status.HTTP_204_NO_CONTENT)


@swagger_auto_schema(
    method='GET',
    query_serializer=AssetListSerializer,
    manual_parameters=[VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM, *PAGINATION_PARAMS],
    responses={200: AssetSerializer},
    operation_summary='List the assets in a version.',
)
@swagger_auto_schema(
    method='POST',
    request_body=AssetRequestSerializer,
    responses={
        200: AssetDetailSerializer,
        404: 'If a blob with the given checksum has not been validated',
    },
    manual_parameters=[VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
    operation_summary='Create an asset.',
    operation_description=(
        'Creates an asset and adds it to a specified version. User must be an owner of the '
        'specified dandiset. New assets can only be attached to draft versions.'
    ),
)
@swagger_auto_schema(
    method='DELETE',
    request_body=AssetBulkDeleteRequestSerializer,
    responses={
        204: 'If the assets were successfully removed',
        404: 'If any of the given assets do not belong to this version',
    },
    manual_parameters=[VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
    operation_summary='Remove assets from a version.',
    operation_description=(
        'Assets are never deleted, only disassociated from a version. Any number of assets '
        'may be removed in a single request, and either all of them are removed, or none '
        'are. Only draft versions can be modified.'
    ),
)
@api_view(['GET', 'HEAD', 'POST', 'DELETE'])
def version_assets_view(request: Request, **kwargs) -> Response:
    if request.method == 'POST':
        return _create_version_asset(request, **kwargs)
    if request.method == 'DELETE':
        return _bulk_delete_version_assets(request, **kwargs)
    return _list_version_assets(request, **kwargs)


@swagger_auto_schema(
    method='GET',
    operation_id='dandisets_versions_assets_paths',
    manual_parameters=[VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM, *PAGINATION_PARAMS],
    query_serializer=AssetPathsQueryParameterSerializer,
    responses={200: AssetPathsSerializer(many=True)},
)
@api_view(['GET', 'HEAD'])
def version_asset_paths_view(
    request: Request, versions__dandiset__pk: str, versions__version: str
) -> Response:
    """
    Return the unique files/directories that directly reside under the specified path.

    The specified path must be a folder; it either must end in a slash or
    (to refer to the root folder) must be the empty string.
    """
    query_serializer = AssetPathsQueryParameterSerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)

    version = get_readable_version_or_404(
        request, dandiset_pk=versions__dandiset__pk, version=versions__version
    )

    # Fetch child paths
    path: str = query_serializer.validated_data['path_prefix']
    children_paths = search_asset_paths(path, version)
    if children_paths is None:
        raise NotFound('Specified path not found.')

    # Paginate and return
    paginator = DandiPagination()
    page = paginator.paginate_queryset(children_paths, request=request)
    serializer = AssetPathsSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


def _get_version_asset(version: Version, asset_id: str) -> Asset:
    """Fetch an asset belonging to the given version."""
    return get_object_or_404(version.assets.select_related('blob', 'zarr'), asset_id=asset_id)


def _retrieve_version_asset(
    request: Request, versions__dandiset__pk: str, versions__version: str, asset_id: str
) -> Response:
    version = get_readable_version_or_404(
        request, dandiset_pk=versions__dandiset__pk, version=versions__version
    )
    asset = _get_version_asset(version, asset_id)
    return Response(asset.full_metadata)


@require_dandiset_owner_or_403('versions__dandiset__pk')
def _update_version_asset(
    request: Request, versions__dandiset__pk: str, versions__version: str, asset_id: str
) -> Response:
    version: Version = get_object_or_404(
        Version.objects.select_related('dandiset'),
        dandiset__pk=versions__dandiset__pk,
        version=versions__version,
    )
    if version.version != 'draft':
        raise DraftDandisetNotModifiableError
    if version.dandiset.unembargo_in_progress:
        raise DandisetUnembargoInProgressError

    serializer = AssetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Lock asset for update
    with transaction.atomic():
        locked_asset = get_object_or_404(version.assets.select_for_update(), asset_id=asset_id)
        asset, _ = change_asset(
            user=request.user,
            asset=locked_asset,
            version=version,
            new_asset_blob=serializer.get_blob(),
            new_zarr_archive=serializer.get_zarr_archive(),
            new_metadata=serializer.validated_data['metadata'],
        )

    return Response(AssetDetailSerializer(instance=asset).data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='GET',
    manual_parameters=[ASSET_ID_PARAM, VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
    responses={
        200: 'The asset metadata.',
    },
    operation_summary="Get an asset's metadata",
)
@swagger_auto_schema(
    method='PUT',
    request_body=AssetRequestSerializer,
    responses={200: AssetDetailSerializer},
    manual_parameters=[ASSET_ID_PARAM, VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
    operation_summary='Create an asset with updated metadata.',
    operation_description=(
        'User must be an owner of the associated dandiset. Only draft versions can be '
        'modified. Old asset is returned if no updates to metadata are made.'
    ),
)
@api_view(['GET', 'HEAD', 'PUT'])
def version_asset_view(request: Request, **kwargs) -> Response:
    if request.method == 'PUT':
        return _update_version_asset(request, **kwargs)
    return _retrieve_version_asset(request, **kwargs)


@swagger_auto_schema(
    method='GET',
    operation_id='dandisets_versions_assets_download',
    operation_summary='Get the download link for an asset.',
    operation_description='',
    manual_parameters=[
        ASSET_ID_PARAM,
        VERSIONS_DANDISET_PK_PARAM,
        VERSIONS_VERSION_PARAM,
    ],
    responses={
        200: None,  # This disables the auto-generated 200 response
        301: 'Redirect to object store',
    },
)
@api_view(['GET', 'HEAD'])
def version_asset_download_view(
    request: Request, versions__dandiset__pk: str, versions__version: str, asset_id: str
) -> HttpResponse:
    version = get_readable_version_or_404(
        request, dandiset_pk=versions__dandiset__pk, version=versions__version
    )
    asset = _get_version_asset(version, asset_id)
    return _asset_download_response(request, asset)


@swagger_auto_schema(
    method='GET',
    operation_id='dandisets_versions_assets_info',
    operation_summary='Django serialization of an asset',
    manual_parameters=[
        ASSET_ID_PARAM,
        VERSIONS_DANDISET_PK_PARAM,
        VERSIONS_VERSION_PARAM,
    ],
    responses={200: AssetDetailSerializer},
)
@api_view(['GET', 'HEAD'])
def version_asset_info_view(
    request: Request, versions__dandiset__pk: str, versions__version: str, asset_id: str
) -> Response:
    """Django serialization of an asset."""
    version = get_readable_version_or_404(
        request, dandiset_pk=versions__dandiset__pk, version=versions__version
    )
    asset = _get_version_asset(version, asset_id)
    serializer = AssetDetailSerializer(instance=asset)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='GET',
    operation_id='dandisets_versions_assets_validation',
    responses={200: AssetValidationSerializer},
    manual_parameters=[
        ASSET_ID_PARAM,
        VERSIONS_DANDISET_PK_PARAM,
        VERSIONS_VERSION_PARAM,
    ],
    operation_summary='Get any validation errors associated with an asset',
    operation_description='',
)
@api_view(['GET', 'HEAD'])
def version_asset_validation_view(
    request: Request, versions__dandiset__pk: str, versions__version: str, asset_id: str
) -> Response:
    version = get_readable_version_or_404(
        request, dandiset_pk=versions__dandiset__pk, version=versions__version
    )
    asset = _get_version_asset(version, asset_id)
    serializer = AssetValidationSerializer(instance=asset)
    return Response(serializer.data, status=status.HTTP_200_OK)


# TODO: add create to forge an asset from a validation
