from __future__ import annotations

from typing import List

from django.http.response import HttpResponseBase
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from s3_file_field._multipart import MultipartManager, TransferredPart, TransferredParts

from dandiapi.api.models import AssetBlob, Upload
from dandiapi.api.tasks import calculate_sha256
from dandiapi.api.views.serializers import AssetBlobSerializer


class DigestSerializer(serializers.Serializer):
    algorithm = serializers.CharField()
    value = serializers.CharField()


class UploadInitializationRequestSerializer(serializers.Serializer):
    contentSize = serializers.IntegerField(min_value=1)  # noqa: N815
    digest = DigestSerializer()


class PartInitializationResponseSerializer(serializers.Serializer):
    part_number = serializers.IntegerField(min_value=1)
    size = serializers.IntegerField(min_value=1)
    upload_url = serializers.URLField()


class MultipartInitializationResponseSerializer(serializers.Serializer):
    object_key = serializers.CharField(trim_whitespace=False)
    upload_id = serializers.CharField()
    parts = PartInitializationResponseSerializer(many=True, allow_empty=False)


class UploadInitializationResponseSerializer(serializers.Serializer):
    uuid = serializers.CharField()
    multipart_upload = MultipartInitializationResponseSerializer()


class PartCompletionRequestSerializer(serializers.Serializer):
    part_number = serializers.IntegerField(min_value=1)
    size = serializers.IntegerField(min_value=1)
    etag = serializers.CharField()

    def create(self, validated_data) -> TransferredPart:
        return TransferredPart(**validated_data)


class UploadCompletionRequestSerializer(serializers.Serializer):
    parts = PartCompletionRequestSerializer(many=True, allow_empty=False)

    def create(self, validated_data) -> List[TransferredPart]:
        return [
            TransferredPart(**part)
            for part in sorted(validated_data.pop('parts'), key=lambda part: part['part_number'])
        ]


class UploadCompletionResponseSerializer(serializers.Serializer):
    complete_url = serializers.URLField()
    body = serializers.CharField(trim_whitespace=False)


@swagger_auto_schema(
    method='POST',
    request_body=DigestSerializer(),
    responses={200: AssetBlobSerializer()},
)
@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([])
def blob_read_view(request: Request) -> HttpResponseBase:
    """Fetch an existing asset blob by digest, if it exists."""
    request_serializer = DigestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    if request_serializer.validated_data['algorithm'] != 'dandi:dandi-etag':
        return Response('Unsupported Digest Algorithm', status=400)
    etag = request_serializer.validated_data['value']

    asset_blob = get_object_or_404(AssetBlob, etag=etag)
    response_serializer = AssetBlobSerializer(asset_blob)
    return Response(response_serializer.data)


@swagger_auto_schema(
    method='POST',
    request_body=UploadInitializationRequestSerializer(),
    responses={
        200: UploadInitializationResponseSerializer(),
        409: 'Blob already exists. '
        'The Location header will be set to the UUID of the existing asset blob.',
    },
)
@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([IsAuthenticated])
def upload_initialize_view(request: Request) -> HttpResponseBase:
    """
    Initialize a multipart upload.

    A list of parts will be returned, each of which has a presigned upload URL and a size.
    This URL communicates directly with the object store so the client can upload bytes directly.

    https://docs.aws.amazon.com/AmazonS3/latest/dev/mpuoverview.html
    """
    request_serializer = UploadInitializationRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    content_size = request_serializer.validated_data['contentSize']
    digest = request_serializer.validated_data['digest']
    if digest['algorithm'] != 'dandi:dandi-etag':
        return Response('Unsupported Digest Type', status=400)
    etag = digest['value']

    assets = AssetBlob.objects.filter(etag=etag)
    if assets.exists():
        return Response(
            'Blob already exists.',
            status=status.HTTP_409_CONFLICT,
            headers={'Location': assets.first().uuid},
        )

    upload, initialization = Upload.initialize_multipart_upload(etag, content_size)
    upload.save()

    response_serializer = UploadInitializationResponseSerializer(initialization)
    return Response(response_serializer.data)


@swagger_auto_schema(
    method='POST',
    request_body=UploadCompletionRequestSerializer(),
    responses={200: UploadCompletionResponseSerializer()},
)
@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([IsAuthenticated])
def upload_complete_view(request: Request, uuid: str) -> HttpResponseBase:
    """
    Complete a multipart upload.

    After all data has been uploaded using the URLs provided by initialize, this endpoint must
    be called to create the object in the object store. A presigned URL that performs the
    completion is returned, as the completion might take several minutes for large files.
    """
    request_serializer = UploadCompletionRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    parts: List[TransferredPart] = request_serializer.save()

    upload = get_object_or_404(Upload, uuid=uuid)

    completion = TransferredParts(
        object_key=upload.blob.name,
        upload_id=str(upload.upload_id),
        parts=parts,
    )

    completed_upload = MultipartManager.from_storage(AssetBlob.blob.field.storage).complete_upload(
        completion
    )

    response_serializer = UploadCompletionResponseSerializer(
        {
            'complete_url': completed_upload.complete_url,
            'body': completed_upload.body,
        }
    )
    return Response(response_serializer.data)


@swagger_auto_schema(
    method='POST',
    responses={
        200: 'The asset blob for the uploaded data.',
        400: 'The specified upload has not completed or has failed.',
    },
)
@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([IsAuthenticated])
def upload_validate_view(request: Request, uuid: str) -> HttpResponseBase:
    """
    Verify that an upload completed successfully and mint a new AssetBlob.

    Also starts the asynchronous checksum calculation process.
    """
    upload = get_object_or_404(Upload, uuid=uuid)

    # Verify that the upload was successful
    if not upload.object_key_exists():
        raise ValidationError('Object does not exist.')
    if upload.size != upload.actual_size():
        raise ValidationError('Size does not match.')
    if upload.etag != upload.actual_etag():
        raise ValidationError('ETag does not match.')

    try:
        # Perhaps another upload completed before this one and has already created an AssetBlob.
        asset_blob = AssetBlob.objects.get(etag=upload.etag, size=upload.size)
    except AssetBlob.DoesNotExist:
        asset_blob = upload.to_asset_blob()
        asset_blob.save()

    # Clean up the upload
    upload.delete()

    # Start calculating the sha256 in the background
    calculate_sha256.delay(asset_blob.uuid)

    response_serializer = AssetBlobSerializer(asset_blob)
    return Response(response_serializer.data, status=status.HTTP_200_OK)
