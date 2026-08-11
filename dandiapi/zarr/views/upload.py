from __future__ import annotations

import logging
import typing
from typing import TYPE_CHECKING

from django.db import transaction
from django.http.response import Http404, HttpResponseBase
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from dandiapi.api.permissions import AuthenticatedRequest, IsApproved
from dandiapi.api.services import audit
from dandiapi.api.services.embargo.exceptions import DandisetUnembargoInProgressError
from dandiapi.api.services.exceptions import NotAllowedError
from dandiapi.api.services.permissions.dandiset import is_dandiset_owner
from dandiapi.api.views.upload import (
    DigestSerializer,
    UploadCompletionRequestSerializer,
    UploadCompletionResponseSerializer,
    UploadInitializationResponseSerializer,
    complete_multipart_upload,
)
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus, ZarrUpload, ZarrUploadType

if TYPE_CHECKING:
    from collections import OrderedDict

    from s3_file_field._multipart import TransferredPart

logger = logging.getLogger(__name__)


class ZarrUploadInitializationRequestSerializer(serializers.Serializer):
    zarr_id = serializers.UUIDField()
    chunk_key = serializers.CharField()
    contentSize = serializers.IntegerField(min_value=1)  # noqa: N815
    digest = DigestSerializer()

    def get_digest_data(self) -> tuple[str, int]:
        """Return a tuple of (etag, content_size), raising an exception if invalid."""
        self.is_valid(raise_exception=True)

        data = typing.cast('OrderedDict', self.validated_data)
        digest = data['digest']
        if digest['algorithm'] != 'dandi:dandi-etag':
            raise ValidationError('Unsupported Digest Type')

        return digest['value'], self.validated_data['contentSize']


class ZarrUploadValidationResponseSerializer(serializers.Serializer):
    zarr_id = serializers.UUIDField()
    chunk_key = serializers.CharField()


@swagger_auto_schema(
    method='POST',
    request_body=ZarrUploadInitializationRequestSerializer,
    responses={
        200: UploadInitializationResponseSerializer,
        400: 'The zarr archive does not support multipart upload.',
    },
)
@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([IsApproved])
def zarr_upload_initialize_view(request: AuthenticatedRequest) -> HttpResponseBase:
    """
    Initialize a multipart upload of a zarr chunk.

    A list of parts will be returned, each of which has a presigned upload URL and a size.
    This URL communicates directly with the object store so the client can upload bytes directly.

    https://docs.aws.amazon.com/AmazonS3/latest/dev/mpuoverview.html
    """
    request_serializer = ZarrUploadInitializationRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)

    etag, content_size = request_serializer.get_digest_data()
    data: dict = request_serializer.validated_data

    zarr_archive: ZarrArchive = get_object_or_404(ZarrArchive, zarr_id=data['zarr_id'])
    dandiset = zarr_archive.dandiset
    if not is_dandiset_owner(dandiset, request.user):
        raise NotAllowedError

    # Ensure dandiset not in the process of unembargo
    if dandiset.unembargo_in_progress:
        raise DandisetUnembargoInProgressError

    # This is the multipart upload flow. A single-part zarr's chunks must be uploaded
    # through the single-part flow, or its checksum cannot be reconciled.
    if zarr_archive.upload_type != ZarrUploadType.MULTIPART:
        raise ValidationError('This zarr archive does not support multipart upload.')

    if zarr_archive.status in [ZarrArchiveStatus.UPLOADED, ZarrArchiveStatus.INGESTING]:
        raise ValidationError(ZarrArchive.INGEST_ERROR_MSG)

    upload, initialization = ZarrUpload.initialize_multipart_upload(
        etag, content_size, zarr=zarr_archive, chunk_key=data['chunk_key']
    )
    with transaction.atomic():
        upload.save()
        audit.upload_zarr_chunks(
            dandiset=dandiset,
            user=request.user,
            zarr_archive=zarr_archive,
            paths=[upload.chunk_key],
        )

    logger.info(
        'Zarr upload initialized for chunk %s of zarr %s', upload.chunk_key, zarr_archive.zarr_id
    )

    response_serializer = UploadInitializationResponseSerializer(initialization)
    return Response(response_serializer.data)


@swagger_auto_schema(
    method='POST',
    request_body=UploadCompletionRequestSerializer,
    responses={200: UploadCompletionResponseSerializer},
)
@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([IsApproved])
def zarr_upload_complete_view(request: AuthenticatedRequest, upload_id: str) -> HttpResponseBase:
    """
    Complete a multipart upload of a zarr chunk.

    After all data has been uploaded using the URLs provided by initialize, this endpoint must
    be called to create the object in the object store. A presigned URL that performs the
    completion is returned, as the completion might take several minutes for large files.
    """
    request_serializer = UploadCompletionRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    parts: list[TransferredPart] = request_serializer.save()

    upload: ZarrUpload = get_object_or_404(ZarrUpload, upload_id=upload_id)
    if upload.embargoed and not is_dandiset_owner(upload.zarr.dandiset, request.user):
        raise Http404 from None

    return complete_multipart_upload(upload, parts)


@swagger_auto_schema(
    method='POST',
    responses={
        200: ZarrUploadValidationResponseSerializer,
        400: 'The specified upload has not completed or has failed.',
    },
)
@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([IsApproved])
def zarr_upload_validate_view(request: AuthenticatedRequest, upload_id: str) -> HttpResponseBase:
    """
    Verify that a zarr chunk upload completed successfully.

    This marks the zarr archive as pending, since a new file has been added to it.
    """
    upload: ZarrUpload = get_object_or_404(ZarrUpload, upload_id=upload_id)
    zarr = upload.zarr
    if upload.embargoed and not is_dandiset_owner(zarr.dandiset, request.user):
        raise Http404 from None

    # This raises an exception if unsuccessful
    upload.validate_successful()

    # Grab this before deleting the upload
    chunk_key = upload.chunk_key

    with transaction.atomic():
        upload.delete()

        # Zarr must be marked pending since a new file is now added
        zarr.mark_pending()
        zarr.save()

    response_serializer = ZarrUploadValidationResponseSerializer(
        {'zarr_id': zarr.zarr_id, 'chunk_key': chunk_key}
    )
    return Response(response_serializer.data, status=status.HTTP_200_OK)
