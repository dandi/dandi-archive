from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http.response import HttpResponseRedirect
from django.urls import reverse
from drf_yasg import openapi
from drf_yasg.utils import no_body, swagger_auto_schema
from minio_storage.storage import MinioStorage
from rest_framework import serializers, status
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from storages.backends.s3boto3 import S3Boto3Storage

from dandiapi.api.models import ZarrArchive, ZarrUploadFile
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.tasks import cancel_zarr_upload
from dandiapi.api.tasks.zarr import ingest_zarr_archive
from dandiapi.api.views.common import DandiPagination
from dandiapi.api.zarr_checksums import ZarrChecksumFileUpdater


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


class ZarrExploreSerializer(serializers.Serializer):
    directories = serializers.ListField(child=serializers.URLField())
    files = serializers.ListField(child=serializers.URLField())
    checksums = serializers.DictField(
        child=serializers.RegexField('^[0-9a-f]{32}(-[0-9]+--[0-9]+)?$')
    )
    checksum = serializers.RegexField('^[0-9a-f]{32}-[0-9]+--[0-9]+$')


class ZarrListSerializer(serializers.Serializer):
    dandiset = serializers.RegexField(Dandiset.IDENTIFIER_REGEX, required=False)
    name = serializers.CharField(required=False)


class ZarrViewSet(ReadOnlyModelViewSet):
    serializer_class = ZarrSerializer
    pagination_class = DandiPagination

    queryset = ZarrArchive.objects.all()
    lookup_field = 'zarr_id'
    lookup_value_regex = ZarrArchive.UUID_REGEX

    def get_queryset(self):
        query_serializer = ZarrListSerializer(data=self.request.query_params)
        query_serializer.is_valid(raise_exception=True)

        # Filter by search params
        queryset = self.queryset
        data = query_serializer.validated_data
        if 'dandiset' in data:
            queryset = queryset.filter(dandiset=int(data['dandiset'].lstrip('0')))
        if 'name' in data:
            queryset = queryset.filter(name=data['name'])

        return queryset

    @swagger_auto_schema(
        query_serializer=ZarrListSerializer(),
        responses={200: ZarrSerializer(many=True)},
        operation_summary='List zarr archives.',
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
        queryset = self.get_queryset().select_for_update()
        with transaction.atomic():
            zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)
            if zarr_archive.status == ZarrArchive.Status.INGESTING:
                return Response(ZarrArchive.INGEST_ERROR_MSG, status=status.HTTP_400_BAD_REQUEST)

            if not self.request.user.has_perm('owner', zarr_archive.dandiset):
                # The user does not have ownership permission
                raise PermissionDenied()
            print(f'Beginning upload to zarr archive {zarr_archive.zarr_id}')
            serializer = ZarrUploadFileRequestSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            uploads = zarr_archive.begin_upload(serializer.validated_data)

        serializer = ZarrUploadBatchSerializer(instance=uploads, many=True)
        print(f'Presigned {len(uploads)} URLs to upload to zarr archive {zarr_archive.zarr_id}')
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
        queryset = self.get_queryset().select_for_update()
        with transaction.atomic():
            zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)
            if not self.request.user.has_perm('owner', zarr_archive.dandiset):
                # The user does not have ownership permission
                raise PermissionDenied()
            print(f'Beggining upload completion for zarr archive {zarr_archive.zarr_id}')
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
        cancel_zarr_upload.delay()
        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        method='DELETE',
        request_body=ZarrDeleteFileRequestSerializer(many=True),
        responses={
            200: ZarrSerializer(many=True),
            400: ZarrArchive.INGEST_ERROR_MSG,
        },
        operation_summary='Delete files from a zarr archive.',
        operation_description='',
    )
    @action(methods=['DELETE'], url_path='files', detail=True)
    def delete_files(self, request, zarr_id):
        """Delete files from a zarr archive."""
        queryset = self.get_queryset().select_for_update()
        with transaction.atomic():
            zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)
            if zarr_archive.status == ZarrArchive.Status.INGESTING:
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

        if zarr_archive.status != ZarrArchive.Status.PENDING:
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
        200: ZarrExploreSerializer(),
        302: 'Redirect to an object in S3',
    },
    manual_parameters=[
        openapi.Parameter(
            'path',
            openapi.IN_PATH,
            'a file or directory path within the zarr file.',
            type=openapi.TYPE_STRING,
            required=True,
            pattern=r'.*',
        )
    ],
    operation_id='zarr_content_read',
)
@api_view(['GET', 'HEAD'])
def explore_zarr_archive(request, zarr_id: str, path: str):
    """
    Get information about files in a zarr archive.

    If the path ends with /, it is assumed to be a directory and metadata about the directory is returned.
    If the path does not end with /, it is assumed to be a file and a redirect to that file in S3 is returned.
    HEAD requests are all assumed to be files and will return redirects to that file in S3.

    This API is compatible with https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.implementations.http.HTTPFileSystem.
    """  # noqa: E501
    zarr_archive = get_object_or_404(ZarrArchive, zarr_id=zarr_id)
    if path == '':
        path = '/'
    if request.method == 'HEAD':
        # We cannot use storage.url because that presigns a GET request.
        # Instead, we need to presign the HEAD request using the storage-appropriate client.
        storage = ZarrUploadFile.blob.field.storage
        if issubclass(storage.__class__, S3Boto3Storage):
            url = storage.bucket.meta.client.generate_presigned_url(
                'head_object',
                Params={'Bucket': storage.bucket.name, 'Key': zarr_archive.s3_path(path)},
            )
        elif issubclass(storage.__class__, MinioStorage):
            url = storage.base_url_client.presigned_url(
                'HEAD', storage.bucket_name, zarr_archive.s3_path(path)
            )
        return HttpResponseRedirect(url)
    # If a path ends with a /, assume it is a directory.
    # Return a JSON blob which contains URLs to the contents of the directory.
    if path.endswith('/'):
        # Strip off the trailing /, it confuses the ZarrChecksumFileUpdater
        path = path.rstrip('/')
        # We use the .checksum file to determine the directory contents, since S3 cannot.
        listing = ZarrChecksumFileUpdater(
            zarr_archive=zarr_archive, zarr_directory_path=path
        ).read_checksum_file()
        if listing is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        directories = [
            settings.DANDI_API_URL
            + reverse('zarr-explore', args=[zarr_id, str(Path(path) / directory.name)])
            + '/'
            for directory in listing.checksums.directories
        ]
        files = [
            settings.DANDI_API_URL
            + reverse('zarr-explore', args=[zarr_id, str(Path(path) / file.name)])
            for file in listing.checksums.files
        ]
        checksums = {
            **{directory.name: directory.digest for directory in listing.checksums.directories},
            **{file.name: file.digest for file in listing.checksums.files},
        }
        serializer = ZarrExploreSerializer(
            data={
                'directories': directories,
                'files': files,
                'checksums': checksums,
                'checksum': listing.digest,
            }
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
    else:
        # The path did not end in a /, so it was a file.
        # Redirect to a presigned S3 URL.
        # S3 will 404 if the file does not exist.
        return HttpResponseRedirect(
            ZarrUploadFile.blob.field.storage.url(zarr_archive.s3_path(path))
        )
