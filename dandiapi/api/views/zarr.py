from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_yasg import openapi
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from dandiapi.api.models import ZarrArchive, ZarrUploadFile
from dandiapi.api.permissions import IsApprovedOrReadOnly
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


class ZarrSerializer(serializers.Serializer):
    class Meta:
        model = ZarrArchive
        fields = [
            'zarr_id',
            'name',
            'checksum',
            'file_count',
            'size',
        ]
        read_only_fields = ['zarr_id', 'checksum', 'file_count', 'size']

    zarr_id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=512)
    checksum = serializers.CharField(max_length=40, read_only=True)
    file_count = serializers.IntegerField(read_only=True)
    size = serializers.IntegerField(read_only=True)


class ZarrViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsApprovedOrReadOnly]
    serializer_class = ZarrSerializer
    pagination_class = DandiPagination

    queryset = ZarrArchive.objects.all()
    lookup_field = 'zarr_id'
    lookup_value_regex = ZarrArchive.UUID_REGEX

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
        zarr_archive: ZarrArchive = ZarrArchive(name=name)
        zarr_archive.save()

        serializer = ZarrSerializer(instance=zarr_archive)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='POST',
        request_body=ZarrUploadFileRequestSerializer(many=True),
        responses={200: ZarrUploadBatchSerializer(many=True)},
        operation_summary='Start an upload of files to a zarr archive.',
        operation_description='',
    )
    @action(methods=['POST'], detail=True)
    def upload(self, request, zarr_id):
        """Start an upload of files to a zarr archive."""
        queryset = self.get_queryset().select_for_update()
        with transaction.atomic():
            zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)
            serializer = ZarrUploadFileRequestSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)

            uploads = zarr_archive.begin_upload(serializer.validated_data)

        serializer = ZarrUploadBatchSerializer(instance=uploads, many=True)
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

            zarr_archive.complete_upload()

        return Response(None, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={200: ZarrSerializer(many=True)},
        operation_summary='Cancel an upload of files to a zarr archive.',
        operation_description='',
    )
    @upload.mapping.delete
    def upload_cancel(self, request, zarr_id):
        """Cancel an upload of files to a zarr archive."""
        queryset = self.get_queryset().select_for_update()
        with transaction.atomic():
            zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)

            zarr_archive.cancel_upload()

        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        method='DELETE',
        request_body=ZarrDeleteFileRequestSerializer(many=True),
        responses={200: ZarrSerializer(many=True)},
        operation_summary='Delete files from a zarr archive.',
        operation_description='',
    )
    @action(methods=['DELETE'], url_path='files', detail=True)
    def delete_files(self, request, zarr_id):
        """Delete files from a zarr archive."""
        queryset = self.get_queryset().select_for_update()
        with transaction.atomic():
            zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)
            serializer = ZarrDeleteFileRequestSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            paths = [file['path'] for file in serializer.validated_data]
            zarr_archive.delete_files(paths)
        return Response(None, status=status.HTTP_204_NO_CONTENT)


@swagger_auto_schema(
    method='GET',
    responses={
        200: 'foobar',
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
)
@api_view(['GET'])
def explore_zarr_archive(request, zarr_id: str, path: str):
    zarr_archive = get_object_or_404(ZarrArchive, zarr_id=zarr_id)
    if path == '':
        path = '/'
    # If a path ends with a /, assume it is a directory.
    # Return a JSON blob which contains URLs to the contents of the directory.
    if path.endswith('/'):
        # Strip off the trailing /, it confuses the ZarrChecksumFileUpdater
        path = path[:-1]
        # We use the .checksum file to determine the directory contents, since S3 cannot.
        listing = ZarrChecksumFileUpdater(
            zarr_archive=zarr_archive, zarr_directory_path=path
        ).read_checksum_file()
        if listing is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        directories = [
            settings.DANDI_API_URL + reverse('zarr-explore', args=[zarr_id, directory.path])
            for directory in listing.checksums.directories
        ]
        files = [
            settings.DANDI_API_URL + reverse('zarr-explore', args=[zarr_id, file.path])
            for file in listing.checksums.files
        ]
        return Response({'directories': directories, 'files': files})
    else:
        # The path did not end in a /, so it was a file.
        # Redirect to a presigned S3 URL.
        # S3 will 404 if the file does not exist.
        return HttpResponseRedirect(
            ZarrUploadFile.blob.field.storage.url(zarr_archive.s3_path(path))
        )
