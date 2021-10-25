try:
    from storages.backends.s3boto3 import S3Boto3Storage
except ImportError:
    # This should only be used for type interrogation, never instantiation
    S3Boto3Storage = type('FakeS3Boto3Storage', (), {})
try:
    from minio_storage.storage import MinioStorage
except ImportError:
    # This should only be used for type interrogation, never instantiation
    MinioStorage = type('FakeMinioStorage', (), {})

import os.path
from typing import Union
from urllib.parse import urlencode

from django.db import models, transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from guardian.decorators import permission_required_or_403
from rest_framework import serializers, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandiapi.api.models import Asset, AssetBlob, Dandiset, Version
from dandiapi.api.permissions import IsApprovedOrReadOnly
from dandiapi.api.tasks import validate_asset_metadata
from dandiapi.api.views.common import (
    ASSET_ID_PARAM,
    PATH_PREFIX_PARAM,
    VERSIONS_DANDISET_PK_PARAM,
    VERSIONS_VERSION_PARAM,
    DandiPagination,
)
from dandiapi.api.views.serializers import (
    AssetDetailSerializer,
    AssetPathsSerializer,
    AssetSerializer,
    AssetValidationSerializer,
)


def _download_asset(asset: Asset):
    storage = asset.blob.blob.storage

    if isinstance(storage, S3Boto3Storage):
        client = storage.connection.meta.client
        path = os.path.basename(asset.path)
        url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': storage.bucket_name,
                'Key': asset.blob.blob.name,
                'ResponseContentDisposition': f'attachment; filename="{path}"',
            },
        )
        return HttpResponseRedirect(url)
    elif isinstance(storage, MinioStorage):
        client = storage.client if storage.base_url is None else storage.base_url_client
        bucket = storage.bucket_name
        obj = asset.blob.blob.name
        path = os.path.basename(asset.path)
        url = client.presigned_get_object(
            bucket,
            obj,
            response_headers={'response-content-disposition': f'attachment; filename="{path}"'},
        )
        return HttpResponseRedirect(url)
    else:
        raise ValueError(f'Unknown storage {storage}')


@swagger_auto_schema(
    method='GET',
    operation_summary='Get the download link for an asset.',
    operation_description='',
    manual_parameters=[ASSET_ID_PARAM],
)
@api_view(['GET', 'HEAD'])
def asset_download_view(request, asset_id):
    asset = get_object_or_404(Asset, asset_id=asset_id)
    return _download_asset(asset)


@swagger_auto_schema(
    method='GET',
    operation_summary="Get an asset's metadata",
    manual_parameters=[ASSET_ID_PARAM],
)
@api_view(['GET', 'HEAD'])
def asset_metadata_view(request, asset_id):
    asset = get_object_or_404(Asset, asset_id=asset_id)
    return JsonResponse(asset.metadata)


class AssetRequestSerializer(serializers.Serializer):
    metadata = serializers.JSONField()
    blob_id = serializers.UUIDField()


class AssetFilter(filters.FilterSet):
    path = filters.CharFilter(lookup_expr='istartswith')
    order = filters.OrderingFilter(fields=['created', 'modified', 'path'])

    class Meta:
        model = Asset
        fields = ['path']


class AssetViewSet(NestedViewSetMixin, DetailSerializerMixin, ReadOnlyModelViewSet):
    queryset = Asset.objects.all().order_by('created')

    permission_classes = [IsApprovedOrReadOnly]
    serializer_class = AssetSerializer
    serializer_detail_class = AssetDetailSerializer
    pagination_class = DandiPagination

    lookup_field = 'asset_id'
    lookup_value_regex = Asset.UUID_REGEX

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = AssetFilter

    @swagger_auto_schema(
        responses={
            200: 'The asset metadata.',
        },
        manual_parameters=[ASSET_ID_PARAM, VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
        operation_summary="Get an asset\'s metadata",
        operation_description='',
    )
    def retrieve(self, request, **kwargs):
        asset = self.get_object()
        return Response(asset.metadata, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        responses={200: AssetValidationSerializer()},
        manual_parameters=[ASSET_ID_PARAM, VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
        operation_summary='Get any validation errors associated with an asset',
        operation_description='',
    )
    @action(detail=True, methods=['GET'])
    def validation(self, request, **kwargs):
        asset = self.get_object()
        serializer = AssetValidationSerializer(instance=asset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=AssetRequestSerializer(),
        responses={
            200: AssetDetailSerializer(),
            404: 'If a blob with the given checksum has not been validated',
        },
        manual_parameters=[VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
        operation_summary='Create an asset.',
        operation_description='Creates an asset and adds it to a specified version.\
                               User must be an owner of the specified dandiset.\
                               New assets can only be attached to draft versions.',
    )
    @method_decorator(
        permission_required_or_403('owner', (Dandiset, 'pk', 'versions__dandiset__pk'))
    )
    def create(self, request, versions__dandiset__pk, versions__version):
        version: Version = get_object_or_404(
            Version,
            dandiset=versions__dandiset__pk,
            version=versions__version,
        )
        if version.version != 'draft':
            return Response(
                'Only draft versions can be modified.',
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        serializer = AssetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        asset_blob = get_object_or_404(AssetBlob, blob_id=serializer.validated_data['blob_id'])

        metadata = serializer.validated_data['metadata']
        if 'path' not in metadata:
            return Response('No path specified in metadata.', status=400)
        path = metadata['path']

        # Check if there are already any assets with the same path
        if version.assets.filter(path=path).exists():
            return Response(
                'An asset with that path already exists',
                status=status.HTTP_409_CONFLICT,
            )

        # Strip away any computed fields
        metadata = Asset.strip_metadata(metadata)

        asset = Asset(
            path=path,
            blob=asset_blob,
            metadata=metadata,
            status=Asset.Status.PENDING,
        )
        asset.save()
        version.assets.add(asset)

        # Trigger a version metadata validation, as saving the version might change the metadata
        version.status = Version.Status.PENDING
        # Save the version so that the modified field is updated
        version.save()

        # Refresh the blob to be sure the sha256 values is up to date
        asset.blob.refresh_from_db()
        # If the blob is still waiting to have it's checksum calculated, there's no point in
        # validating now; in fact, it could cause a race condition. Once the blob's sha256 is
        # calculated, it will revalidate this asset.
        # If the blob already has a sha256, then the asset metadata is ready to validate.
        if asset.blob.sha256 is not None:
            # We do not bother to delay it because it should run very quickly.
            validate_asset_metadata(asset.id)

        serializer = AssetDetailSerializer(instance=asset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=AssetRequestSerializer(),
        responses={200: AssetDetailSerializer()},
        manual_parameters=[VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
        operation_summary='Update the metadata of an asset.',
        operation_description='User must be an owner of the associated dandiset.\
                               Only draft versions can be modified.',
    )
    @method_decorator(
        permission_required_or_403('owner', (Dandiset, 'pk', 'versions__dandiset__pk'))
    )
    def update(self, request, versions__dandiset__pk, versions__version, **kwargs):
        """Update the metadata of an asset."""
        old_asset = self.get_object()
        version = get_object_or_404(
            Version,
            dandiset__pk=versions__dandiset__pk,
            version=versions__version,
        )
        if version.version != 'draft':
            return Response(
                'Only draft versions can be modified.',
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        serializer = AssetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        asset_blob = get_object_or_404(AssetBlob, blob_id=serializer.validated_data['blob_id'])

        metadata = serializer.validated_data['metadata']
        if 'path' not in metadata:
            return Response('No path specified in metadata', status=404)
        path = metadata['path']
        # Strip away any computed fields
        metadata = Asset.strip_metadata(metadata)

        if metadata == old_asset.metadata and asset_blob == old_asset.blob:
            # No changes, don't create a new asset
            new_asset = old_asset
        else:
            # Verify we aren't changing path to the same value as an existing asset
            if (
                version.assets.filter(path=path)
                .filter(~models.Q(asset_id=old_asset.asset_id))
                .exists()
            ):
                return Response(
                    'An asset with that path already exists',
                    status=status.HTTP_409_CONFLICT,
                )

            with transaction.atomic():
                # Mint a new Asset whenever blob or metadata are modified
                new_asset = Asset(
                    path=path,
                    blob=asset_blob,
                    metadata=metadata,
                    previous=old_asset,
                    status=Asset.Status.PENDING,
                )
                new_asset.save()

                # Replace the old asset with the new one
                version.assets.add(new_asset)
                version.assets.remove(old_asset)

        # Trigger a version metadata validation, as saving the version might change the metadata
        version.status = Version.Status.PENDING
        # Save the version so that the modified field is updated
        version.save()

        # Refresh the blob to be sure the sha256 values is up to date
        new_asset.blob.refresh_from_db()
        # If the blob is still waiting to have it's checksum calculated, there's no point in
        # validating now; in fact, it could cause a race condition. Once the blob's sha256 is
        # calculated, it will revalidate this asset.
        # If the blob already has a sha256, then the asset metadata is ready to validate.
        if new_asset.blob.sha256 is not None:
            # We do not bother to delay it because it should run very quickly.
            validate_asset_metadata(new_asset.id)

        serializer = AssetDetailSerializer(instance=new_asset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @method_decorator(
        permission_required_or_403('owner', (Dandiset, 'pk', 'versions__dandiset__pk'))
    )
    @swagger_auto_schema(
        manual_parameters=[VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
        operation_summary='Remove an asset from a version.',
        operation_description='Assets are never deleted, only disassociated from a version.\
                               Only draft versions can be modified.',
    )
    def destroy(self, request, versions__dandiset__pk, versions__version, **kwargs):
        asset = self.get_object()
        version = get_object_or_404(
            Version,
            dandiset__pk=versions__dandiset__pk,
            version=versions__version,
        )
        if version.version != 'draft':
            return Response(
                'Only draft versions can be modified.',
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        version.assets.remove(asset)

        # Trigger a version metadata validation, as saving the version might change the metadata
        version.status = Version.Status.PENDING
        # Save the version so that the modified field is updated
        version.save()

        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        responses={
            200: None,  # This disables the auto-generated 200 response
            301: 'Redirect to object store',
        },
        manual_parameters=[ASSET_ID_PARAM, VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
        operation_summary='Return a redirect to the file download in the object store.',
        operation_description='',
    )
    @action(detail=True, methods=['GET'])
    def download(self, request, **kwargs):
        """Return a redirect to the file download in the object store."""
        return _download_asset(self.get_object())

    @swagger_auto_schema(
        manual_parameters=[PATH_PREFIX_PARAM],
        responses={200: AssetPathsSerializer()},
    )
    @action(detail=False, methods=['GET'])
    def paths(self, request, versions__dandiset__pk: str, versions__version: str, **kwargs):
        """
        Return the unique files/directories that directly reside under the specified path.

        The specified path must be a folder; it either must end in a slash or
        (to refer to the root folder) must be the empty string.
        """
        path_prefix: str = self.request.query_params.get('path_prefix') or ''
        page: int = int(self.request.query_params.get('page') or '1')
        page_size: int = int(
            self.request.query_params.get('page_size') or DandiPagination.page_size
        )
        qs = self.get_queryset().select_related('blob').filter(path__startswith=path_prefix)

        assets: dict[str, Union[Asset, dict]] = {}

        for asset in qs:
            # Get the remainder of the path after path_prefix
            base_path: str = asset.path[len(path_prefix) :].strip('/')

            # Since we stripped slashes, any remaining slashes indicate a folder
            folder_index = base_path.find('/')
            is_folder = folder_index >= 0

            if not is_folder:
                assets[base_path] = asset
            else:
                base_path = base_path[:folder_index]
                entry = assets.get(base_path)
                if entry is None:
                    assets[base_path] = {
                        'size': asset.size,
                        'num_files': 1,
                        'created': asset.created,
                        'modified': asset.modified,
                    }
                else:
                    entry['size'] += asset.size
                    entry['num_files'] += 1
                    entry['created'] = min(entry['created'], asset.created)  # earliest
                    entry['modified'] = max(entry['modified'], asset.modified)  # latest

        asset_count = len(assets)

        # Paginate response
        assets = dict(list(assets.items())[(page - 1) * page_size : page * page_size])
        paths = AssetPathsSerializer(
            {
                'folders': {k: v for k, v in assets.items() if not isinstance(v, Asset)},
                'files': {k: v for k, v in assets.items() if isinstance(v, Asset)},
            }
        )
        url_kwargs = {
            'versions__dandiset__pk': versions__dandiset__pk,
            'versions__version': versions__version,
        }
        url = reverse('asset-paths', kwargs=url_kwargs)
        max_page = asset_count // page_size
        next_page = page + 1 if page + 1 <= max_page else None
        prev_page = page - 1 if page - 1 > 0 else None
        next_url = None
        prev_url = None
        if next_page is not None:
            next_url = f'{url}?{urlencode({"page": next_page, "page_size": page_size})}'
        if prev_page is not None:
            prev_url = f'{url}?{urlencode({"page": prev_page, "page_size": page_size})}'

        resp = {'results': paths.data, 'count': asset_count, 'next': next_url, 'previous': prev_url}
        return Response(resp)

    # TODO: add create to forge an asset from a validation
