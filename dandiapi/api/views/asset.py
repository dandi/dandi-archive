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

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from guardian.decorators import permission_required_or_403
from rest_framework import serializers, status
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandiapi.api.models import Asset, AssetBlob, AssetMetadata, Dandiset, Version
from dandiapi.api.tasks import validate_asset_metadata, validate_version_metadata
from dandiapi.api.views.common import DandiPagination
from dandiapi.api.views.serializers import (
    AssetDetailSerializer,
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
        client = storage.base_url_client
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


@swagger_auto_schema()
@api_view(['GET', 'HEAD'])
def asset_download_view(request, asset_id):
    asset = Asset.objects.get(asset_id=asset_id)
    return _download_asset(asset)


class AssetRequestSerializer(serializers.Serializer):
    metadata = serializers.JSONField()
    blob_id = serializers.UUIDField()


class AssetUpdateRequestSerializer(serializers.Serializer):
    metadata = serializers.JSONField(required=False)
    blob_id = serializers.UUIDField(required=False)


class AssetFilter(filters.FilterSet):
    path = filters.CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Asset
        fields = ['path']


class AssetViewSet(NestedViewSetMixin, DetailSerializerMixin, ReadOnlyModelViewSet):
    queryset = Asset.objects.all().order_by('created')

    permission_classes = [IsAuthenticatedOrReadOnly]
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
    )
    def retrieve(self, request, **kwargs):
        asset = self.get_object()
        return Response(asset.metadata.metadata, status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: AssetValidationSerializer()})
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
        # Strip away any computed fields
        metadata = Asset.strip_metadata(metadata)
        asset_metadata, created = AssetMetadata.objects.get_or_create(metadata=metadata)
        if created:
            asset_metadata.save()

        asset = Asset(
            path=path,
            blob=asset_blob,
            metadata=asset_metadata,
        )
        asset.save()
        version.assets.add(asset)

        # Save the version so that the modified field is updated
        version.save()

        # Trigger a version metadata validation, as saving the version might change the metadata
        validate_version_metadata.delay(version.id)

        # Trigger an asset metadata validation
        # This will fail if the digest hasn't been calculated yet, but we still need to try now
        # just in case we are using an existing blob that has already computed its digest.
        validate_asset_metadata.delay(asset.id)

        serializer = AssetDetailSerializer(instance=asset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=AssetUpdateRequestSerializer(),
        responses={200: AssetDetailSerializer()},
    )
    @method_decorator(
        permission_required_or_403('owner', (Dandiset, 'pk', 'versions__dandiset__pk'))
    )
    def update(self, request, versions__dandiset__pk, versions__version, **kwargs):
        """Update the metadata of an asset."""
        old_asset = self.get_object()
        version = Version.objects.get(
            dandiset__pk=versions__dandiset__pk,
            version=versions__version,
        )
        if version.version != 'draft':
            return Response(
                'Only draft versions can be modified.',
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        serializer = AssetUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if 'blob_id' in serializer.validated_data:
            asset_blob = get_object_or_404(AssetBlob, blob_id=serializer.validated_data['blob_id'])
        else:
            asset_blob = old_asset.blob

        if 'metadata' in serializer.validated_data:
            metadata = serializer.validated_data['metadata']
            if 'path' not in metadata:
                return Response('No path specified in metadata', status=404)
            path = metadata['path']
            # Strip away any computed fields
            metadata = Asset.strip_metadata(metadata)
            asset_metadata, created = AssetMetadata.objects.get_or_create(metadata=metadata)
            if created:
                asset_metadata.save()
        else:
            asset_metadata = old_asset.metadata

        if asset_metadata == old_asset.metadata and asset_blob == old_asset.blob:
            # No changes, don't create a new asset
            new_asset = old_asset
        else:
            # Mint a new Asset whenever blob or metadata are modified
            new_asset = Asset(
                path=path,
                blob=asset_blob,
                metadata=asset_metadata,
                previous=old_asset,
            )
            new_asset.save()

            # Replace the old asset with the new one
            version.assets.add(new_asset)
            version.assets.remove(old_asset)

        # Save the version so that the modified field is updated
        version.save()

        # Trigger a version metadata validation, as saving the version might change the metadata
        validate_version_metadata.delay(version.id)

        # Trigger an asset metadata validation
        # This will fail if the digest hasn't been calculated yet, but we still need to try now
        # just in case we are using an existing blob that has already computed its digest.
        validate_asset_metadata.delay(new_asset.id)

        serializer = AssetDetailSerializer(instance=new_asset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @method_decorator(
        permission_required_or_403('owner', (Dandiset, 'pk', 'versions__dandiset__pk'))
    )
    def destroy(self, request, versions__dandiset__pk, versions__version, **kwargs):
        asset = self.get_object()
        version = Version.objects.get(
            dandiset__pk=versions__dandiset__pk, version=versions__version
        )
        if version.version != 'draft':
            return Response(
                'Only draft versions can be modified.',
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        version.assets.remove(asset)

        # Save the version so that the modified field is updated
        version.save()

        # Trigger a version metadata validation, as saving the version might change the metadata
        validate_version_metadata.delay(version.id)

        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        responses={
            200: None,  # This disables the auto-generated 200 response
            301: 'Redirect to object store',
        }
    )
    @action(detail=True, methods=['GET'])
    def download(self, request, **kwargs):
        """Return a redirect to the file download in the object store."""
        return _download_asset(self.get_object())

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('path_prefix', openapi.IN_QUERY, type=openapi.TYPE_STRING)
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_STRING),
            )
        },
    )
    @action(detail=False, methods=['GET'])
    def paths(self, request, **kwargs):
        """
        Return the unique files/directories that directly reside under the specified path.

        The specified path must be a folder; it either must end in a slash or
        (to refer to the root folder) must be the empty string.
        """
        path_prefix: str = self.request.query_params.get('path_prefix') or ''
        # Enforce trailing slash
        if path_prefix and path_prefix[-1] != '/':
            path_prefix = f'{path_prefix}/'
        qs = self.get_queryset().filter(path__startswith=path_prefix).values()

        return Response(Asset.get_path(path_prefix, qs))

    # TODO: add create to forge an asset from a validation
