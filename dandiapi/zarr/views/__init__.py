from __future__ import annotations

import logging
from pathlib import Path

from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from django.db.models.query import QuerySet
from django.http import HttpResponseRedirect
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param
from rest_framework.viewsets import ReadOnlyModelViewSet

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.storage import get_boto_client
from dandiapi.api.views.common import DandiPagination
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus, ZarrUploadFile
from dandiapi.zarr.tasks import cancel_zarr_upload, ingest_zarr_archive

logger = logging.getLogger(__name__)


class ZarrUploadFileSerializer(serializers.Serializer):
    class Meta:
        model = ZarrUploadFile
        fields = [
            'blob',
            'etag',
        ]


class ZarrUploadFileRequestSerializer(serializers.Serializer):
    class Meta:
        model = ZarrUploadFile
        fields = [
            'path',
            'etag',
        ]

    path = serializers.CharField()
    etag = serializers.CharField()


class ZarrUploadBatchSerializer(serializers.Serializer):
    class Meta:
        model = ZarrUploadFile
        fields = [
            'path',
            'upload_url',
        ]

    path = serializers.CharField()
    upload_url = serializers.URLField()


class ZarrDeleteFileRequestSerializer(serializers.Serializer):
    path = serializers.CharField()


class ZarrSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZarrArchive
        read_only_fields = [
            'zarr_id',
            'status',
            'checksum',
            'upload_in_progress',
            'file_count',
            'size',
        ]
        fields = ['name', 'dandiset', *read_only_fields]

    dandiset = serializers.RegexField(f'^{Dandiset.IDENTIFIER_REGEX}$')


class ZarrListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZarrArchive
        read_only_fields = [
            'zarr_id',
            'status',
            'checksum',
            'upload_in_progress',
            'file_count',
            'size',
        ]
        fields = ['name', 'dandiset', *read_only_fields]

    dandiset = serializers.RegexField(f'^{Dandiset.IDENTIFIER_REGEX}$')
    upload_in_progress = serializers.BooleanField(source='uploads_exist')


class ZarrExploreInputSerializer(serializers.Serializer):
    after = serializers.CharField(default='')
    prefix = serializers.CharField(default='')
    limit = serializers.IntegerField(min_value=0, max_value=1000, default=1000)
    download = serializers.BooleanField(default=False)


class ZarrExploreOutputSerializer(serializers.Serializer):
    class ResultsSerializer(serializers.Serializer):
        Key = serializers.CharField()
        LastModified = serializers.CharField()
        ETag = serializers.CharField()
        Size = serializers.IntegerField(min_value=0)

    next = serializers.CharField(default=None)
    results = serializers.ListField(child=ResultsSerializer())


class ZarrListQuerySerializer(serializers.Serializer):
    dandiset = serializers.RegexField(Dandiset.IDENTIFIER_REGEX, required=False)
    name = serializers.CharField(required=False)


class ZarrViewSet(ReadOnlyModelViewSet):
    serializer_class = ZarrSerializer
    pagination_class = DandiPagination

    queryset = ZarrArchive.objects.select_related('dandiset').order_by('created').all()
    lookup_field = 'zarr_id'
    lookup_value_regex = ZarrArchive.UUID_REGEX

    @swagger_auto_schema(
        query_serializer=ZarrListQuerySerializer(),
        responses={200: ZarrListSerializer(many=True)},
        operation_summary='List zarr archives.',
    )
    def list(self, request, *args, **kwargs):
        query_serializer = ZarrListQuerySerializer(data=self.request.query_params)
        query_serializer.is_valid(raise_exception=True)

        # Add filters from query parameters
        data = query_serializer.validated_data
        queryset: QuerySet[ZarrArchive] = self.get_queryset()
        if 'dandiset' in data:
            queryset = queryset.filter(dandiset=int(data['dandiset'].lstrip('0')))
        if 'name' in data:
            queryset = queryset.filter(name=data['name'])

        # Add active uploads annotation
        queryset = queryset.annotate(
            uploads_exist=Exists(ZarrUploadFile.objects.filter(zarr_archive_id=OuterRef('id')))
        )

        # Final response
        queryset = self.paginate_queryset(queryset)
        serializer = ZarrListSerializer(queryset, many=True)
        return self.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        request_body=ZarrSerializer(),
        responses={200: ZarrSerializer()},
        operation_summary='Create a new zarr archive.',
        operation_description='',
    )
    def create(self, request):
        """Create a new zarr archive."""
        serializer = ZarrSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data['name']
        dandiset = get_object_or_404(
            Dandiset.objects.visible_to(request.user), id=serializer.validated_data['dandiset']
        )
        if not self.request.user.has_perm('owner', dandiset):
            raise PermissionDenied()
        if dandiset.embargo_status != Dandiset.EmbargoStatus.OPEN:
            raise ValidationError('Cannot add zarr to embargoed dandiset')
        zarr_archive: ZarrArchive = ZarrArchive(name=name, dandiset=dandiset)
        try:
            zarr_archive.save()
        except IntegrityError:
            raise ValidationError('Zarr already exists')

        serializer = ZarrSerializer(instance=zarr_archive)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='POST',
        request_body=ZarrUploadFileRequestSerializer(many=True),
        responses={
            200: ZarrUploadBatchSerializer(many=True),
            400: ZarrArchive.INGEST_ERROR_MSG,
        },
        operation_summary='Start an upload of files to a zarr archive.',
        operation_description='',
    )
    @action(methods=['POST'], detail=True)
    def upload(self, request, zarr_id):
        """Start an upload of files to a zarr archive."""
        # reset select_related to prevent locking additional rows
        queryset = self.get_queryset().select_related(None).select_for_update()
        with transaction.atomic():
            zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)
            if zarr_archive.status == ZarrArchiveStatus.INGESTING:
                return Response(ZarrArchive.INGEST_ERROR_MSG, status=status.HTTP_400_BAD_REQUEST)

            if not self.request.user.has_perm('owner', zarr_archive.dandiset):
                # The user does not have ownership permission
                raise PermissionDenied()
            logger.info(f'Beginning upload to zarr archive {zarr_archive.zarr_id}')
            serializer = ZarrUploadFileRequestSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            uploads = zarr_archive.begin_upload(serializer.validated_data)

        serializer = ZarrUploadBatchSerializer(instance=uploads, many=True)
        logger.info(
            f'Presigned {len(uploads)} URLs to upload to zarr archive {zarr_archive.zarr_id}'
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='POST',
        request_body=no_body,
        responses={200: ZarrSerializer(many=True), 400: 'Incomplete or incorrect upload.'},
        operation_summary='Finish an upload of files to a zarr archive.',
        operation_description='',
    )
    @action(methods=['POST'], url_path='upload/complete', detail=True)
    def upload_complete(self, request, zarr_id):
        """Finish an upload of files to a zarr archive."""
        # reset select_related to prevent locking additional rows
        queryset = self.get_queryset().select_related(None).select_for_update()
        with transaction.atomic():
            zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)
            if not self.request.user.has_perm('owner', zarr_archive.dandiset):
                # The user does not have ownership permission
                raise PermissionDenied()
            logger.info(f'Beginning upload completion for zarr archive {zarr_archive.zarr_id}')
            zarr_archive.complete_upload()
            # Save any zarr assets to trigger metadata updates
            for asset in zarr_archive.assets.all():
                asset.save()

        return Response(None, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={200: ZarrSerializer(many=True)},
        operation_summary='Cancel an upload of files to a zarr archive.',
        operation_description='',
    )
    @upload.mapping.delete
    def upload_cancel(self, request, zarr_id):
        """Cancel an upload of files to a zarr archive."""
        queryset = self.get_queryset()
        zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)
        if not self.request.user.has_perm('owner', zarr_archive.dandiset):
            raise PermissionDenied()
        if not zarr_archive.upload_in_progress:
            raise ValidationError('No upload to cancel.')
        # Cancelling involves deleting any data uploaded to S3, which involves a batch of S3 API
        # requests. These are done in a task to avoid Heroku request timeouts.
        cancel_zarr_upload.delay(zarr_id)
        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        method='POST',
        request_body=no_body,
        responses={
            # Note: Having proper None results in no documentation in /swagger
            204: 'None - expected normal return without any content',
            400: ZarrArchive.INGEST_ERROR_MSG,
        },
        operation_summary='Ingest a zarr archive, calculating checksums, size and file count.',
        operation_description='',
    )
    @action(methods=['POST'], detail=True)
    def ingest(self, request, zarr_id):
        """Ingest a zarr archive."""
        zarr_archive: ZarrArchive = get_object_or_404(self.get_queryset(), zarr_id=zarr_id)
        if not self.request.user.has_perm('owner', zarr_archive.dandiset):
            # The user does not have ownership permission
            raise PermissionDenied()

        if zarr_archive.status != ZarrArchiveStatus.PENDING:
            return Response(ZarrArchive.INGEST_ERROR_MSG, status=status.HTTP_400_BAD_REQUEST)
        if zarr_archive.upload_in_progress:
            return Response(
                'Upload in progress. Please cancel or complete this existing upload.',
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Dispatch ingestion
        ingest_zarr_archive.delay(zarr_id=zarr_archive.zarr_id)

        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        method='GET',
        responses={
            200: 'Listing of s3 objects',
            302: 'Redirect to an object in S3',
        },
        query_serializer=ZarrExploreInputSerializer(),
    )
    @action(methods=['HEAD', 'GET'], detail=True)
    def files(self, request, zarr_id: str):
        """List files in a zarr archive."""
        zarr_archive = get_object_or_404(ZarrArchive, zarr_id=zarr_id)
        serializer = ZarrExploreInputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # The root path for this zarr in s3
        base_path = Path(zarr_archive.s3_path(''))

        # Retrieve and join query params
        limit = serializer.validated_data['limit']
        download = serializer.validated_data['download']

        raw_prefix = serializer.validated_data['prefix']
        full_prefix = str(base_path / raw_prefix)

        _after = serializer.validated_data['after']
        after = str(base_path / _after) if _after else ''

        # Handle head request redirects
        if request.method == 'HEAD':
            # We cannot use storage.url because that presigns a GET request.
            # Instead, we need to presign the HEAD request using the storage-appropriate client.
            storage = ZarrUploadFile.blob.field.storage
            url = storage.generate_presigned_head_object_url(full_prefix)
            return HttpResponseRedirect(url)

        # Return a redirect to the file, if requested
        # S3 will 404 if the file does not exist.
        if download:
            return HttpResponseRedirect(
                ZarrUploadFile.blob.field.storage.url(zarr_archive.s3_path(raw_prefix))
            )

        # Retrieve file listing
        client = get_boto_client()
        listing = client.list_objects_v2(
            Bucket=zarr_archive.storage.bucket_name,
            Prefix=full_prefix,
            StartAfter=after,
            MaxKeys=limit,
        )

        # Map/filter listing
        results = [
            {
                'Key': str(Path(obj['Key']).relative_to(base_path)),
                'LastModified': obj['LastModified'],
                'ETag': obj['ETag'].strip('"'),
                'Size': obj['Size'],
            }
            for obj in listing.get('Contents', [])
        ]

        # Create next listing if necessary
        next_link = None
        if listing['IsTruncated']:
            url = self.request.build_absolute_uri()
            next_link = replace_query_param(url, 'after', results[-1]['Key'])

        # Construct serializer and return
        return Response(
            ZarrExploreOutputSerializer(
                instance={
                    'next': next_link,
                    'results': results,
                }
            ).data
        )

    @swagger_auto_schema(
        request_body=ZarrDeleteFileRequestSerializer(many=True),
        responses={
            200: ZarrSerializer(many=True),
            400: ZarrArchive.INGEST_ERROR_MSG,
        },
        operation_summary='Delete files from a zarr archive.',
    )
    @files.mapping.delete
    def delete_files(self, request, zarr_id):
        """Delete files from a zarr archive."""
        queryset = self.get_queryset().select_for_update()
        with transaction.atomic():
            zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)
            if zarr_archive.status == ZarrArchiveStatus.INGESTING:
                return Response(ZarrArchive.INGEST_ERROR_MSG, status=status.HTTP_400_BAD_REQUEST)

            if not self.request.user.has_perm('owner', zarr_archive.dandiset):
                # The user does not have ownership permission
                raise PermissionDenied()
            serializer = ZarrDeleteFileRequestSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            paths = [file['path'] for file in serializer.validated_data]
            zarr_archive.delete_files(paths)

            # Save any zarr assets to trigger metadata updates
            for asset in zarr_archive.assets.all():
                asset.save()
        return Response(None, status=status.HTTP_204_NO_CONTENT)
