from __future__ import annotations

import re
import typing

from django.contrib.auth.models import User

from dandiapi.api.asset_paths import search_asset_paths
from dandiapi.api.services.asset import (
    add_asset_to_version,
    change_asset,
    remove_asset_from_version,
)
from dandiapi.api.services.asset.exceptions import DraftDandisetNotModifiableError
from dandiapi.api.services.embargo.exceptions import DandisetUnembargoInProgressError
from dandiapi.api.services.permissions.dandiset import (
    is_dandiset_owner,
    is_owned_asset,
    require_dandiset_owner_or_403,
)
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


from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandiapi.api.models import Asset, AssetBlob, Dandiset, Version
from dandiapi.api.models.asset import validate_asset_path
from dandiapi.api.views.common import (
    ASSET_ID_PARAM,
    VERSIONS_DANDISET_PK_PARAM,
    VERSIONS_VERSION_PARAM,
)
from dandiapi.api.views.pagination import DandiPagination, LazyPagination
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

    def raise_if_unauthorized(self):
        # We need to check the dandiset to see if it's embargoed, and if so whether or not the
        # user has ownership
        asset_id = self.kwargs.get('asset_id')
        if asset_id is None:
            return

        asset = get_object_or_404(Asset.objects.select_related('blob', 'zarr'), asset_id=asset_id)
        if not asset.is_embargoed:
            return

        # Clients must be authenticated to access it
        if not self.request.user.is_authenticated:
            raise NotAuthenticated
        self.request.user = typing.cast(User, self.request.user)

        # Admins are allowed to access any embargoed asset blob
        if self.request.user.is_superuser:
            return

        # User must be an owner on any of the dandisets this asset belongs to
        is_owned = is_owned_asset(asset, self.request.user)
        if not is_owned:
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
        asset_blob = asset.blob

        # Redirect to correct presigned URL
        storage = asset_blob.blob.storage

        serializer = AssetDownloadQueryParameterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        content_disposition = serializer.validated_data['content_disposition']
        content_type = asset.metadata.get('encodingFormat', 'application/octet-stream')
        asset_basename = asset.path.split('/')[-1]

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

        data['metadata'].setdefault('schemaVersion', settings.DANDI_SCHEMA_VERSION)
        return data


class NestedAssetViewSet(NestedViewSetMixin, AssetViewSet, ReadOnlyModelViewSet):
    pagination_class = DandiPagination

    def raise_if_unauthorized(self):
        version = get_object_or_404(
            Version.objects.select_related('dandiset'),
            dandiset__pk=self.kwargs['versions__dandiset__pk'],
            version=self.kwargs['versions__version'],
        )
        if version.dandiset.embargo_status != Dandiset.EmbargoStatus.OPEN:
            if not self.request.user.is_authenticated:
                # Clients must be authenticated to access it
                raise NotAuthenticated
            if not is_dandiset_owner(version.dandiset, self.request.user):
                # The user does not have ownership permission
                raise PermissionDenied

    # Override this here to prevent the need for raise_if_unauthorized to exist in get_queryset
    def get_object(self):
        self.raise_if_unauthorized()
        return super().get_object()

    # Override this to skip the call to raise_if_unauthorized in AssetViewSet
    def get_queryset(self):
        return super(AssetViewSet, self).get_queryset()

    # Redefine info and download actions to update swagger manual_parameters

    @swagger_auto_schema(
        method='GET',
        operation_summary='Django serialization of an asset',
        manual_parameters=[
            ASSET_ID_PARAM,
            VERSIONS_DANDISET_PK_PARAM,
            VERSIONS_VERSION_PARAM,
        ],
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
    @action(detail=True, methods=['GET'])
    def download(self, *args, **kwargs):
        return super().download(*args, **kwargs)

    # Remaining actions

    @swagger_auto_schema(
        responses={200: AssetValidationSerializer},
        manual_parameters=[
            ASSET_ID_PARAM,
            VERSIONS_DANDISET_PK_PARAM,
            VERSIONS_VERSION_PARAM,
        ],
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
    @require_dandiset_owner_or_403('versions__dandiset__pk')
    def create(self, request, versions__dandiset__pk, versions__version):
        version: Version = get_object_or_404(
            Version.objects.select_related('dandiset'),
            dandiset=versions__dandiset__pk,
            version=versions__version,
        )

        if version.dandiset.unembargo_in_progress:
            raise DandisetUnembargoInProgressError

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
        operation_summary='Create an asset with updated metadata.',
        operation_description='User must be an owner of the associated dandiset.\
                               Only draft versions can be modified.\
                               Old asset is returned if no updates to metadata are made.',
    )
    @require_dandiset_owner_or_403('versions__dandiset__pk')
    def update(self, request, versions__dandiset__pk, versions__version, **kwargs):
        """Create an asset with updated metadata."""
        version: Version = get_object_or_404(
            Version.objects.select_related('dandiset'),
            dandiset__pk=versions__dandiset__pk,
            version=versions__version,
        )
        if version.version != 'draft':
            raise DraftDandisetNotModifiableError
        if version.dandiset.unembargo_in_progress:
            raise DandisetUnembargoInProgressError

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

    @require_dandiset_owner_or_403('versions__dandiset__pk')
    @swagger_auto_schema(
        manual_parameters=[VERSIONS_DANDISET_PK_PARAM, VERSIONS_VERSION_PARAM],
        operation_summary='Remove an asset from a version.',
        operation_description='Assets are never deleted, only disassociated from a version.\
                               Only draft versions can be modified.',
    )
    def destroy(self, request, versions__dandiset__pk, versions__version, **kwargs):
        version = get_object_or_404(
            Version.objects.select_related('dandiset'),
            dandiset__pk=versions__dandiset__pk,
            version=versions__version,
        )
        if version.dandiset.unembargo_in_progress:
            raise DandisetUnembargoInProgressError

        # Lock asset for delete
        with transaction.atomic():
            locked_asset = get_object_or_404(
                version.assets.select_for_update(), id=self.get_object().id
            )
            remove_asset_from_version(user=request.user, asset=locked_asset, version=version)

        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(query_serializer=AssetListSerializer, responses={200: AssetSerializer})
    def list(self, request, *args, **kwargs):
        # Manually call this to ensure user is authorized
        self.raise_if_unauthorized()

        serializer = AssetListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # Retrieve version first and then fetch assets, to remove a join
        version = Version.objects.get(
            dandiset__pk=self.kwargs['versions__dandiset__pk'],
            version=self.kwargs['versions__version'],
        )

        # Apply filtering from included filter class first
        asset_queryset = self.filter_queryset(version.assets.all())

        # Must do glob pattern matching before pagination
        glob_pattern: str | None = serializer.validated_data.get('glob')
        if glob_pattern is not None:
            # Escape special characters in the glob pattern. This is a security precaution taken
            # since we are using postgres' regex search. A malicious user who knows this could
            # include a regex as part of the glob expression, which postgres would happily parse
            # and use if it's not escaped.
            glob_pattern = f'^{re.escape(glob_pattern)}$'
            asset_queryset = asset_queryset.filter(path__iregex=glob_pattern.replace('\\*', '.*'))

        # Retrieve just the first N asset IDs, and use them for pagination
        # Use custom pagination class to reduce unnecessary counts of assets
        paginator = LazyPagination()
        qs = asset_queryset.values_list('id', flat=True)
        page_of_asset_ids = paginator.paginate_queryset(qs, request=self.request, view=self)

        # Not sure when the page is ever None, but this condition is checked for compatibility with
        # the original implementation: https://github.com/encode/django-rest-framework/blob/f4194c4684420ac86485d9610adf760064db381f/rest_framework/mixins.py#L37-L46
        # This is checked here since the query can't continue if the page is `None` anyway
        if page_of_asset_ids is None:
            serializer = self.get_serializer(Asset.objects.none(), many=True)
            return Response(serializer.data)

        # Now we can retrieve the actual fully joined rows using the limited number of assets we're
        # going to return
        queryset = self.filter_queryset(
            Asset.objects.filter(id__in=page_of_asset_ids).select_related('blob', 'zarr')
        )

        # Must apply this to the main queryset, since it affects the data returned
        include_metadata = serializer.validated_data['metadata']
        if not include_metadata:
            queryset = queryset.defer('metadata')

        # Paginate and return
        serializer = self.get_serializer(queryset, many=True, metadata=include_metadata)
        return paginator.get_paginated_response(serializer.data)

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
