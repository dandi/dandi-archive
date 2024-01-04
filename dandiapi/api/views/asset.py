from __future__ import annotations

import re

from dandiapi.api.asset_paths import search_asset_paths
from dandiapi.api.services.asset import (
    add_asset_to_version,
    change_asset,
    remove_asset_from_version,
)
from dandiapi.api.services.asset.exceptions import DraftDandisetNotModifiableError
from dandiapi.zarr.models import ZarrArchive

try:
    from storages.backends.s3 import S3Storage
except ImportError:
    # This should only be used for type interrogation, never instantiation
    S3Storage = type('FakeS3Storage', (), {})
try:
    from minio_storage.storage import MinioStorage
except ImportError:
    # This should only be used for type interrogation, never instantiation
    MinioStorage = type('FakeMinioStorage', (), {})

import os.path

from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from guardian.decorators import permission_required_or_403
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandiapi.api.models import Asset, AssetBlob, Dandiset, Version
from dandiapi.api.models.asset import EmbargoedAssetBlob, validate_asset_path
from dandiapi.api.views.common import (
    ASSET_ID_PARAM,
    VERSIONS_DANDISET_PK_PARAM,
    VERSIONS_VERSION_PARAM,
    DandiPagination,
)
from dandiapi.api.permissions import IsApproved
from dandiapi.api.views.serializers import (
    AssetDetailSerializer,
    AssetDownloadQueryParameterSerializer,
    AssetListSerializer,
    AssetPathsQueryParameterSerializer,
    AssetPathsSerializer,
    AssetSerializer,
    AssetValidationSerializer,
)


class AssetFilter(filters.FilterSet):
    path = filters.CharFilter(lookup_expr='istartswith')
    order = filters.OrderingFilter(fields=['created', 'modified', 'path'])

    class Meta:
        model = Asset
        fields = ['path']


class AssetViewSet(DetailSerializerMixin, GenericViewSet):
    queryset = Asset.objects.all().select_related('zarr').order_by('created')

    serializer_class = AssetSerializer
    serializer_detail_class = AssetDetailSerializer

    lookup_field = 'asset_id'
    lookup_value_regex = Asset.UUID_REGEX

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = AssetFilter

    permission_classes = [IsApproved]

    def raise_if_unauthorized(self):
        # We need to check the dandiset to see if it's embargoed, and if so whether or not the
        # user has ownership
        asset_id = self.kwargs.get('asset_id')
        if asset_id is not None:
            asset = get_object_or_404(Asset, asset_id=asset_id)
            if asset.embargoed_blob is not None:
                if not self.request.user.is_authenticated:
                    # Clients must be authenticated to access it
                    raise NotAuthenticated
                if not self.request.user.has_perm('owner', asset.embargoed_blob.dandiset):
                    # The user does not have ownership permission
                    raise PermissionDenied

    def get_queryset(self):
        self.raise_if_unauthorized()
        return super().get_queryset()

    @swagger_auto_schema(
        responses={
            200: 'The asset metadata.',
        },
        operation_summary="Get an asset's metadata",
    )
    def retrieve(self, request, **kwargs):
        asset = self.get_object()
        return Response(asset.full_metadata)

    @swagger_auto_schema(
        method='GET',
        operation_summary='Get the download link for an asset.',
        operation_description='',
        query_serializer=AssetDownloadQueryParameterSerializer,
        responses={
            200: None,  # This disables the auto-generated 200 response
            301: 'Redirect to object store',
        },
    )
    @action(methods=['GET', 'HEAD'], detail=True)
    def download(self, request, *args, **kwargs):
        asset = self.get_object()

        # Raise error if zarr
        if asset.is_zarr:
            return Response(
                'Unable to provide download link for zarr assets.'
                ' Please browse the zarr files directly to do so.',
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Assign asset_blob
        if asset.is_blob:
            asset_blob = asset.blob
        elif asset.is_embargoed_blob:
            asset_blob = asset.embargoed_blob

        # Redirect to correct presigned URL
        storage = asset_blob.blob.storage

        serializer = AssetDownloadQueryParameterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        content_disposition = serializer.validated_data['content_disposition']
        content_type = asset.metadata.get('encodingFormat', 'application/octet-stream')
        asset_basename = os.path.basename(asset.path)

        if content_disposition == 'attachment':
            return HttpResponseRedirect(
                storage.generate_presigned_download_url(asset_blob.blob.name, asset_basename)
            )
        if content_disposition == 'inline':
            url = storage.generate_presigned_inline_url(
                asset_blob.blob.name,
                asset_basename,
                content_type,
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
        operation_summary='Django serialization of an asset',
        manual_parameters=[ASSET_ID_PARAM],
        responses={200: AssetDetailSerializer},
    )
    @action(methods=['GET', 'HEAD'], detail=True)
    def info(self, *args, **kwargs):
        asset = self.get_object()
        serializer = AssetDetailSerializer(instance=asset)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AssetRequestSerializer(serializers.Serializer):
    metadata = serializers.JSONField()
    blob_id = serializers.UUIDField(required=False)
    zarr_id = serializers.UUIDField(required=False)

    def get_blob(self) -> AssetBlob | EmbargoedAssetBlob | None:
        asset_blob = None
        embargoed_asset_blob = None

        if 'blob_id' in self.validated_data:
            try:
                asset_blob = AssetBlob.objects.get(blob_id=self.validated_data['blob_id'])
            except AssetBlob.DoesNotExist:
                embargoed_asset_blob = get_object_or_404(
                    EmbargoedAssetBlob, blob_id=self.validated_data['blob_id']
                )

        return asset_blob or embargoed_asset_blob

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

        data['metadata'].setdefault('schemaVersion', settings.DANDI_SCHEMA_VERSION)
        return data


class NestedAssetViewSet(NestedViewSetMixin, AssetViewSet, ReadOnlyModelViewSet):
    pagination_class = DandiPagination
    # Inherited from AssetViewSet -- permission_classes = [IsApproved]

    def raise_if_unauthorized(self):
        version = get_object_or_404(
            Version,
            dandiset__pk=self.kwargs['versions__dandiset__pk'],
            version=self.kwargs['versions__version'],
        )
        if version.dandiset.embargo_status != Dandiset.EmbargoStatus.OPEN:
            if not self.request.user.is_authenticated:
                # Clients must be authenticated to access it
                raise NotAuthenticated
            if not self.request.user.has_perm('owner', version.dandiset):
                # The user does not have ownership permission
                raise PermissionDenied

    # Redefine info and download actions to update swagger manual_parameters

    @swagger_auto_schema(
        method='GET',
        operation_summary='Django serialization of an asset',
        manual_parameters=[ASSET_ID_PARAM, VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
        responses={200: AssetDetailSerializer},
    )
    @action(detail=True, methods=['GET'])
    def info(self, *args, **kwargs):
        """Django serialization of an asset."""
        return super().info()

    @swagger_auto_schema(
        method='GET',
        operation_summary='Get the download link for an asset.',
        operation_description='',
        manual_parameters=[ASSET_ID_PARAM, VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
        responses={
            200: None,  # This disables the auto-generated 200 response
            301: 'Redirect to object store',
        },
    )
    @action(detail=True, methods=['GET'])
    def download(self, *args, **kwargs):
        return super().download(*args, **kwargs)

    # Remaining actions

    @swagger_auto_schema(
        responses={200: AssetValidationSerializer},
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
        request_body=AssetRequestSerializer,
        responses={
            200: AssetDetailSerializer,
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

        serializer = AssetRequestSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)

        asset = add_asset_to_version(
            user=request.user,
            version=version,
            asset_blob=serializer.get_blob(),
            zarr_archive=serializer.get_zarr_archive(),
            metadata=serializer.validated_data['metadata'],
        )

        serializer = AssetDetailSerializer(instance=asset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=AssetRequestSerializer,
        responses={200: AssetDetailSerializer},
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
        version: Version = get_object_or_404(
            Version,
            dandiset__pk=versions__dandiset__pk,
            version=versions__version,
        )
        if version.version != 'draft':
            raise DraftDandisetNotModifiableError

        serializer = AssetRequestSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)

        # Lock asset for update
        with transaction.atomic():
            locked_asset = get_object_or_404(
                version.assets.select_for_update(), id=self.get_object().id
            )
            asset, _ = change_asset(
                user=request.user,
                asset=locked_asset,
                version=version,
                new_asset_blob=serializer.get_blob(),
                new_zarr_archive=serializer.get_zarr_archive(),
                new_metadata=serializer.validated_data['metadata'],
            )

        serializer = AssetDetailSerializer(instance=asset)
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
        version = get_object_or_404(
            Version,
            dandiset__pk=versions__dandiset__pk,
            version=versions__version,
        )

        # Lock asset for delete
        with transaction.atomic():
            locked_asset = get_object_or_404(
                version.assets.select_for_update(), id=self.get_object().id
            )
            remove_asset_from_version(user=request.user, asset=locked_asset, version=version)

        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(query_serializer=AssetListSerializer, responses={200: AssetSerializer})
    def list(self, request, *args, **kwargs):
        serializer = AssetListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # Fetch initial queryset
        queryset: QuerySet[Asset] = self.filter_queryset(
            self.get_queryset().select_related('blob', 'embargoed_blob', 'zarr')
        )

        # Don't include metadata field if not asked for
        include_metadata = serializer.validated_data['metadata']
        if not include_metadata:
            queryset = queryset.defer('metadata')

        glob_pattern: str | None = serializer.validated_data.get('glob')
        if glob_pattern is not None:
            # Escape special characters in the glob pattern. This is a security precaution taken
            # since we are using postgres' regex search. A malicious user who knows this could
            # include a regex as part of the glob expression, which postgres would happily parse
            # and use if it's not escaped.
            glob_pattern = f'^{re.escape(glob_pattern)}$'
            queryset = queryset.filter(path__iregex=glob_pattern.replace('\\*', '.*'))

        # Paginate and return
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, metadata=include_metadata)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, metadata=include_metadata)
        return Response(serializer.data)

    @swagger_auto_schema(
        query_serializer=AssetPathsQueryParameterSerializer,
        responses={200: AssetPathsSerializer(many=True)},
    )
    @action(detail=False, methods=['GET'], filter_backends=[])
    def paths(self, request, versions__dandiset__pk, versions__version, **kwargs):
        """
        Return the unique files/directories that directly reside under the specified path.

        The specified path must be a folder; it either must end in a slash or
        (to refer to the root folder) must be the empty string.
        """
        query_serializer = AssetPathsQueryParameterSerializer(data=self.request.query_params)
        query_serializer.is_valid(raise_exception=True)

        # Permission check
        self.raise_if_unauthorized()

        # Fetch version
        version = get_object_or_404(
            Version,
            dandiset__pk=versions__dandiset__pk,
            version=versions__version,
        )

        # Fetch child paths
        path: str = query_serializer.validated_data['path_prefix']
        children_paths = search_asset_paths(path, version)
        if children_paths is None:
            raise NotFound('Specified path not found.')

        # Paginate and return
        page = self.paginate_queryset(children_paths)
        if page is not None:
            serializer = AssetPathsSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AssetPathsSerializer(children_paths, many=True)
        return Response(serializer.data)

    # TODO: add create to forge an asset from a validation
