from __future__ import annotations

import re

from dandiapi.api.services.asset import search_path
from dandiapi.zarr.models import ZarrArchive

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
from pathlib import PurePosixPath

from django.conf import settings
from django.core.paginator import EmptyPage, Page, Paginator
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpResponseRedirect
from django.http.response import Http404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from guardian.decorators import permission_required_or_403
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandiapi.api.models import Asset, AssetBlob, Dandiset, Version
from dandiapi.api.models.asset import BaseAssetBlob, EmbargoedAssetBlob
from dandiapi.api.tasks import validate_asset_metadata
from dandiapi.api.views.common import (
    ASSET_ID_PARAM,
    VERSIONS_DANDISET_PK_PARAM,
    VERSIONS_VERSION_PARAM,
    DandiPagination,
)
from dandiapi.api.views.serializers import (
    AssetDetailSerializer,
    AssetListSerializer,
    AssetPathsQueryParameterSerializer,
    AssetPathsSerializer,
    AssetSerializer,
    AssetValidationSerializer,
)


def _maybe_validate_asset_metadata(asset: Asset):
    if asset.is_blob:
        blob = asset.blob
    elif asset.is_embargoed_blob:
        blob = asset.embargoed_blob
    else:
        return

    # Refresh the blob to be sure the sha256 values is up to date
    blob: BaseAssetBlob
    blob.refresh_from_db()

    # If the blob is still waiting to have it's checksum calculated, there's no point in
    # validating now; in fact, it could cause a race condition. Once the blob's sha256 is
    # calculated, it will revalidate this asset.
    if blob.sha256 is None:
        return

    # If the blob already has a sha256, then the asset metadata is ready to validate.
    # We do not bother to delay it because it should run very quickly.
    validate_asset_metadata(asset.id)


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

    def raise_if_unauthorized(self):
        # We need to check the dandiset to see if it's embargoed, and if so whether or not the
        # user has ownership
        asset_id = self.kwargs.get('asset_id')
        if asset_id is not None:
            asset = get_object_or_404(Asset, asset_id=asset_id)
            if asset.embargoed_blob is not None:
                if not self.request.user.is_authenticated:
                    # Clients must be authenticated to access it
                    raise NotAuthenticated()
                if not self.request.user.has_perm('owner', asset.embargoed_blob.dandiset):
                    # The user does not have ownership permission
                    raise PermissionDenied()

    def get_queryset(self):
        self.raise_if_unauthorized()
        return super().get_queryset()

    @swagger_auto_schema(
        responses={
            200: 'The asset metadata.',
        },
        operation_summary="Get an asset\'s metadata",
    )
    def retrieve(self, request, **kwargs):
        asset = self.get_object()
        return Response(asset.metadata)

    @swagger_auto_schema(
        method='GET',
        operation_summary='Get the download link for an asset.',
        operation_description='',
        manual_parameters=[ASSET_ID_PARAM],
        responses={
            200: None,  # This disables the auto-generated 200 response
            301: 'Redirect to object store',
        },
    )
    @action(methods=['GET', 'HEAD'], detail=True)
    def download(self, *args, **kwargs):
        asset = self.get_object()

        # Assign asset blob or redirect if zarr
        if asset.is_zarr:
            return HttpResponseRedirect(
                reverse('zarr-explore', kwargs={'zarr_id': asset.zarr.zarr_id, 'path': ''})
            )
        elif asset.is_blob:
            asset_blob = asset.blob
        elif asset.is_embargoed_blob:
            asset_blob = asset.embargoed_blob

        # Redirect to correct presigned URL
        storage = asset_blob.blob.storage
        return HttpResponseRedirect(
            storage.generate_presigned_download_url(
                asset_blob.blob.name, os.path.basename(asset.path)
            )
        )

    @swagger_auto_schema(
        method='GET',
        operation_summary='Django serialization of an asset',
        manual_parameters=[ASSET_ID_PARAM],
        responses={200: AssetDetailSerializer()},
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

    def validate(self, data):
        """Ensure blob_id and zarr_id are mutually exclusive."""
        if ('blob_id' in data) == ('zarr_id' in data):
            raise serializers.ValidationError(
                {'blob_id': 'Exactly one of blob_id or zarr_id must be specified.'}
            )
        if 'path' not in data['metadata'] or not data['metadata']['path']:
            raise serializers.ValidationError({'metadata': 'No path specified in metadata.'})

        path = data['metadata']['path']
        # paths starting with /
        if PurePosixPath(path).is_absolute():
            raise serializers.ValidationError(
                {'metadata': 'Absolute path not allowed for an asset'}
            )

        sub_paths = path.split('/')
        # checking for . in path
        for sub_path in sub_paths:
            if len(set(sub_path)) == 1 and sub_path[0] == '.':
                raise serializers.ValidationError(
                    {'metadata': 'Invalid characters (.) in file path'}
                )

        # match characters repeating more than once
        multiple_occurrence_regex = '[/]{2,}'
        if '\0' in path:
            raise serializers.ValidationError({'metadata': 'Invalid characters (\0) in file name'})
        if re.search(multiple_occurrence_regex, path):
            raise serializers.ValidationError({'metadata': 'Invalid characters (/)) in file name'})

        data['metadata'].setdefault('schemaVersion', settings.DANDI_SCHEMA_VERSION)

        return data


class NestedAssetViewSet(NestedViewSetMixin, AssetViewSet, ReadOnlyModelViewSet):
    pagination_class = DandiPagination

    def raise_if_unauthorized(self):
        version = get_object_or_404(
            Version,
            dandiset__pk=self.kwargs['versions__dandiset__pk'],
            version=self.kwargs['versions__version'],
        )
        if version.dandiset.embargo_status != Dandiset.EmbargoStatus.OPEN:
            if not self.request.user.is_authenticated:
                # Clients must be authenticated to access it
                raise NotAuthenticated()
            if not self.request.user.has_perm('owner', version.dandiset):
                # The user does not have ownership permission
                raise PermissionDenied()

    def _paginate_asset_paths(self, items: dict) -> dict:
        """Paginates a list of files and folders to be returned by the asset paths endpoint."""
        asset_count = len(items)
        page_number = int(self.request.query_params.get(DandiPagination.page_query_param, 1))
        page_size = min(
            int(
                self.request.query_params.get(
                    DandiPagination.page_size_query_param, DandiPagination.page_size
                )
            ),
            DandiPagination.max_page_size,
        )

        paths_paginator: Paginator = Paginator(list(items.items()), page_size)
        try:
            assets_page: Page = paths_paginator.page(page_number)
        except EmptyPage:
            raise Http404()

        # Divide into folders and files
        folders = {}
        files = {}

        # Note that this loop runs in constant time, since the length of assets_page
        # will never exceed DandiPagination.max_page_size.
        for k, v in dict(assets_page).items():
            if isinstance(v, Asset):
                files[k] = v
            else:
                folders[k] = v

        paths = AssetPathsSerializer({'folders': folders, 'files': files})

        # Update url
        url = self.request.build_absolute_uri()
        next_url = (
            replace_query_param(url, DandiPagination.page_query_param, page_number + 1)
            if page_number + 1 <= paths_paginator.num_pages
            else None
        )
        prev_url = (
            replace_query_param(url, DandiPagination.page_query_param, page_number - 1)
            if page_number - 1 > 0
            else None
        )

        return {
            'count': asset_count,
            'next': next_url,
            'previous': prev_url,
            'results': paths.data,
        }

    def asset_from_request(self) -> Asset:
        """
        Return an unsaved Asset, constructed from the request data.

        Any necessary validation errors will be raised in this method.
        """
        serializer = AssetRequestSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)

        asset_blob = None
        embargoed_asset_blob = None
        zarr_archive = None
        if 'blob_id' in serializer.validated_data:
            try:
                asset_blob = AssetBlob.objects.get(blob_id=serializer.validated_data['blob_id'])
            except AssetBlob.DoesNotExist:
                embargoed_asset_blob = get_object_or_404(
                    EmbargoedAssetBlob, blob_id=serializer.validated_data['blob_id']
                )
        elif 'zarr_id' in serializer.validated_data:
            zarr_archive = get_object_or_404(
                ZarrArchive, zarr_id=serializer.validated_data['zarr_id']
            )
        else:
            # This shouldn't ever occur
            raise NotImplementedError('Storage type not handled.')

        # Construct Asset
        path = serializer.validated_data['metadata']['path']
        metadata = Asset.strip_metadata(serializer.validated_data['metadata'])
        asset = Asset(
            path=path,
            blob=asset_blob,
            embargoed_blob=embargoed_asset_blob,
            zarr=zarr_archive,
            metadata=metadata,
            status=Asset.Status.PENDING,
        )

        return asset

    # Redefine info and download actions to update swagger manual_parameters

    @swagger_auto_schema(
        method='GET',
        operation_summary='Django serialization of an asset',
        manual_parameters=[ASSET_ID_PARAM, VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
        responses={200: AssetDetailSerializer()},
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

        # Retrieve blobs and metadata
        asset = self.asset_from_request()

        # Check if there are already any assets with the same path
        if version.assets.filter(path=asset.path).exists():
            return Response(
                'An asset with that path already exists',
                status=status.HTTP_409_CONFLICT,
            )

        # Ensure zarr archive doesn't already belong to a dandiset
        if asset.zarr and asset.zarr.dandiset != version.dandiset:
            raise ValidationError('The zarr archive belongs to a different dandiset')

        asset.save()
        version.assets.add(asset)

        # Trigger a version metadata validation, as saving the version might change the metadata
        version.status = Version.Status.PENDING
        # Save the version so that the modified field is updated
        version.save()

        # Validate the asset metadata if able
        _maybe_validate_asset_metadata(asset)

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
        old_asset: Asset = self.get_object()
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

        # Retrieve blobs and metadata
        new_asset = self.asset_from_request()

        if (
            new_asset.metadata == old_asset.metadata
            and new_asset.blob == old_asset.blob
            and new_asset.embargoed_blob == old_asset.embargoed_blob
            and new_asset.zarr_archive == old_asset.zarr
        ):
            # No changes, don't create a new asset
            new_asset = old_asset
        else:
            # Verify we aren't changing path to the same value as an existing asset
            if (
                version.assets.filter(path=new_asset.path)
                .exclude(asset_id=old_asset.asset_id)
                .exists()
            ):
                return Response(
                    'An asset with that path already exists',
                    status=status.HTTP_409_CONFLICT,
                )

            # Mint a new Asset whenever blob or metadata are modified
            with transaction.atomic():
                # Set previous asset and save
                new_asset.previous = old_asset
                new_asset.save()

                # Replace the old asset with the new one
                version.assets.add(new_asset)
                version.assets.remove(old_asset)

        # Trigger a version metadata validation, as saving the version might change the metadata
        version.status = Version.Status.PENDING
        # Save the version so that the modified field is updated
        version.save()

        # Validate the asset metadata if able
        _maybe_validate_asset_metadata(new_asset)

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

    @swagger_auto_schema(query_serializer=AssetListSerializer, responses={200: AssetSerializer()})
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
            glob_pattern = re.escape(glob_pattern)
            queryset = queryset.filter(path__iregex=glob_pattern.replace('\\*', '.*'))

        # Paginate and return
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, metadata=include_metadata)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, metadata=include_metadata)
        return Response(serializer.data)

    @swagger_auto_schema(
        query_serializer=AssetPathsQueryParameterSerializer(),
        responses={200: AssetPathsSerializer()},
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

        # Fetch version
        version = get_object_or_404(
            Version,
            dandiset__pk=versions__dandiset__pk,
            version=versions__version,
        )

        # Fetch child paths
        path: str = query_serializer.validated_data['path_prefix']
        children_paths = search_path(path, version)
        if children_paths is None:
            raise ValidationError('Specified path not found.')

        # Paginate and return
        page = self.paginate_queryset(children_paths)
        if page is not None:
            serializer = AssetPathsSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AssetPathsSerializer(children_paths, many=True)
        return Response(serializer.data)

    # TODO: add create to forge an asset from a validation
