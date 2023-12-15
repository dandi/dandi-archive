from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import transaction
from django.http.response import Http404, HttpResponseBase
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from guardian.utils import get_40x_or_None
from rest_framework import serializers, status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from s3_file_field._multipart import TransferredPart, TransferredParts

from dandiapi.api.models import AssetBlob, Dandiset, Upload
from dandiapi.api.permissions import IsApproved
from dandiapi.api.tasks import calculate_sha256
from dandiapi.api.views.serializers import AssetBlobSerializer

if TYPE_CHECKING:
    from rest_framework.request import Request

supported_digests = {'dandi:dandi-etag': 'etag', 'dandi:sha2-256': 'sha256'}


class DigestSerializer(serializers.Serializer):
    algorithm = serializers.CharField()
    value = serializers.CharField()


class UploadInitializationRequestSerializer(serializers.Serializer):
    contentSize = serializers.IntegerField(min_value=1)  # noqa: N815
    digest = DigestSerializer()
    dandiset = serializers.RegexField(Dandiset.IDENTIFIER_REGEX)


class PartInitializationResponseSerializer(serializers.Serializer):
    part_number = serializers.IntegerField(min_value=1)
    size = serializers.IntegerField(min_value=1)
    upload_url = serializers.URLField()


class UploadInitializationResponseSerializer(serializers.Serializer):
    upload_id = serializers.CharField()
    parts = PartInitializationResponseSerializer(many=True, allow_empty=False)


class PartCompletionRequestSerializer(serializers.Serializer):
    part_number = serializers.IntegerField(min_value=1)
    size = serializers.IntegerField(min_value=1)
    etag = serializers.CharField()

    def create(self, validated_data) -> TransferredPart:
        return TransferredPart(**validated_data)


class UploadCompletionRequestSerializer(serializers.Serializer):
    parts = PartCompletionRequestSerializer(many=True, allow_empty=False)

    def create(self, validated_data) -> list[TransferredPart]:
        return [
            TransferredPart(**part)
            for part in sorted(validated_data.pop('parts'), key=lambda part: part['part_number'])
        ]


class UploadCompletionResponseSerializer(serializers.Serializer):
    complete_url = serializers.URLField()
    body = serializers.CharField(trim_whitespace=False)


@swagger_auto_schema(
    method='POST',
    operation_summary='Fetch an existing asset blob by digest, if it exists.',
    operation_description=f'Supported digest algorithms: {", ".join(supported_digests)}',
    request_body=DigestSerializer,
    responses={200: AssetBlobSerializer},
)
@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([])
def blob_read_view(request: Request) -> HttpResponseBase:
    request_serializer = DigestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    algorithm = request_serializer.validated_data['algorithm']
    if algorithm not in supported_digests:
        return Response(
            f'Unsupported Digest Algorithm. Supported: {", ".join(supported_digests)}',
            status=400,
        )
    digest = request_serializer.validated_data['value']

    asset_blob = get_object_or_404(AssetBlob, **{supported_digests[algorithm]: digest})
    response_serializer = AssetBlobSerializer(asset_blob)
    return Response(response_serializer.data)


@swagger_auto_schema(
    method='POST',
    request_body=UploadInitializationRequestSerializer,
    responses={
        200: UploadInitializationResponseSerializer,
        409: 'Blob already exists. '
        'The Location header will be set to the UUID of the existing asset blob.',
    },
)
@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([IsApproved])
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
    dandiset_id = request_serializer.validated_data['dandiset']
    dandiset = get_object_or_404(
        Dandiset.objects.visible_to(request.user),
        id=dandiset_id,
    )
    response = get_40x_or_None(request, ['owner'], dandiset, return_403=True)
    if response:
        return response

    logging.info(
        'Starting upload initialization of size %s, ETag %s to dandiset %s',
        content_size,
        etag,
        dandiset,
    )

    asset_blobs = AssetBlob.objects.filter(etag=etag)
    if asset_blobs.exists():
        return Response(
            'Blob already exists.',
            status=status.HTTP_409_CONFLICT,
            headers={'Location': asset_blobs.first().blob_id},
        )

    logging.info('Blob with ETag %s does not yet exist', etag)

    upload, initialization = Upload.initialize_multipart_upload(etag, content_size, dandiset)
    logging.info('Upload of ETag %s initialized', etag)
    upload.save()
    logging.info('Upload of ETag %s saved', etag)

    response_serializer = UploadInitializationResponseSerializer(initialization)
    logging.info('Upload of ETag %s serialized', etag)
    return Response(response_serializer.data)


@swagger_auto_schema(
    method='POST',
    request_body=UploadCompletionRequestSerializer,
    responses={200: UploadCompletionResponseSerializer},
)
@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([IsApproved])
def upload_complete_view(request: Request, upload_id: str) -> HttpResponseBase:
    """
    Complete a multipart upload.

    After all data has been uploaded using the URLs provided by initialize, this endpoint must
    be called to create the object in the object store. A presigned URL that performs the
    completion is returned, as the completion might take several minutes for large files.
    """
    request_serializer = UploadCompletionRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    parts: list[TransferredPart] = request_serializer.save()

    upload: Upload = get_object_or_404(Upload, upload_id=upload_id)
    if upload.embargoed and not request.user.has_perm('owner', upload.dandiset):
        raise Http404 from None

    completion = TransferredParts(
        object_key=upload.blob.name,
        upload_id=str(upload.multipart_upload_id),
        parts=parts,
    )

    completed_upload = upload.blob.field.storage.multipart_manager.complete_upload(completion)

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
        200: AssetBlobSerializer,
        400: 'The specified upload has not completed or has failed.',
    },
)
@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([IsApproved])
def upload_validate_view(request: Request, upload_id: str) -> HttpResponseBase:
    """
    Verify that an upload completed successfully and mint a new AssetBlob.

    Also starts the asynchronous checksum calculation process.
    """
    upload = get_object_or_404(Upload, upload_id=upload_id)
    if upload.embargoed and not request.user.has_perm('owner', upload.dandiset):
        raise Http404 from None

    # Verify that the upload was successful
    if not upload.object_key_exists():
        raise ValidationError('Object does not exist.')
    if upload.size != upload.actual_size():
        raise ValidationError(
            f'Size {upload.size} does not match actual size {upload.actual_size()}.'
        )
    if upload.etag != upload.actual_etag():
        raise ValidationError(
            f'ETag {upload.etag} does not match actual ETag {upload.actual_etag()}.'
        )

    # Use a transaction here so we can use select_for_update to lock the DB rows to avoid
    # a race condition where two clients are uploading the same blob at the same time.
    # This also ensures that the minting of the new AssetBlob and deletion of the Upload
    # is an atomic operation.
    with transaction.atomic():
        try:
            # Perhaps another upload completed before this one and has already created an AssetBlob.
            asset_blob = AssetBlob.objects.select_for_update(no_key=True).get(
                etag=upload.etag, size=upload.size
            )
        except AssetBlob.DoesNotExist:
            asset_blob = upload.to_asset_blob()
            asset_blob.save()

        # Clean up the upload
        upload.delete()

    # Start calculating the sha256 in the background
    calculate_sha256.delay(asset_blob.blob_id)

    response_serializer = AssetBlobSerializer(asset_blob)
    return Response(response_serializer.data, status=status.HTTP_200_OK)
