from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from dandischema.digests.dandietag import PartGenerator
from s3_file_field._multipart import (
    PresignedPartTransfer,
    PresignedTransfer,
    TransferredParts,
    UploadTooLargeError,
)
from s3_file_field._multipart_s3 import S3MultipartManager

from dandiapi.storage import MinioDandiS3Storage

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from dandiapi.storage import DandiS3Storage


class DandiS3MultipartManager(S3MultipartManager):
    """
    Overrides S3MultipartManager to provide DANDI-specific functionality.

    Provides:
    * A longer URL expiration time
    * Support for tagging
    * Different part sizes
    """

    # Overridden with a longer time
    _url_expiration = timedelta(days=7)

    def __init__(self, storage: DandiS3Storage) -> None:
        super().__init__(storage)

        # Make URL generation work when MinioDandiS3Storage and "media_url" are in use;
        # otherwise, this does nothing different. Upstream S3FF supports a "media_url" for
        # MinioMultipartManager, but not S3MultipartManager (as this is specific to
        # MinioDandiS3Storage).
        self._signing_client = (
            storage.media_connection.meta.client
            if isinstance(storage, MinioDandiS3Storage) and storage.media_url
            else self._client
        )

    # Overridden to let dandischema define part sizes:
    # https://github.com/dandi/dandi-archive/issues/160
    @classmethod
    def _iter_part_sizes(cls, file_size: int) -> Iterator[tuple[int, int]]:
        generator = PartGenerator.for_file_size(file_size)
        for part in generator:
            yield part.number, part.size

    # Forked to accept a "tags" parameter
    def _create_upload_id(
        self,
        object_key: str,
        content_type: str,
        *,
        tags: Mapping[str, str] | None = None,
    ) -> str:
        optional_params = {}
        if tags is not None:
            optional_params['Tagging'] = urlencode(tags)

        resp = self._client.create_multipart_upload(
            Bucket=self._bucket_name, Key=object_key, ContentType=content_type, **optional_params
        )
        return resp['UploadId']

    # Forked to use "self._signing_client"
    def _generate_presigned_part_url(
        self, object_key: str, upload_id: str, part_number: int, part_size: int
    ) -> str:
        return self._signing_client.generate_presigned_url(
            ClientMethod='upload_part',
            Params={
                'Bucket': self._bucket_name,
                'Key': object_key,
                'UploadId': upload_id,
                'PartNumber': part_number,
                'ContentLength': part_size,
            },
            ExpiresIn=int(self._url_expiration.total_seconds()),
        )

    # Forked to use "self._signing_client"
    def _generate_presigned_complete_url(self, transferred_parts: TransferredParts) -> str:
        return self._signing_client.generate_presigned_url(
            ClientMethod='complete_multipart_upload',
            Params={
                'Bucket': self._bucket_name,
                'Key': transferred_parts.object_key,
                'UploadId': transferred_parts.upload_id,
            },
            ExpiresIn=int(self._url_expiration.total_seconds()),
        )

    # Forked to accept a "tags" parameter
    def initialize_upload(
        self,
        object_key: str,
        file_size: int,
        content_type: str,
        *,
        tags: Mapping[str, str] | None = None,
    ) -> PresignedTransfer:
        if file_size > self.max_object_size:
            raise UploadTooLargeError('File is larger than the S3 maximum object size.')

        upload_id = self._create_upload_id(object_key, content_type, tags=tags)
        parts = [
            PresignedPartTransfer(
                part_number=part_number,
                size=part_size,
                upload_url=self._generate_presigned_part_url(
                    object_key, upload_id, part_number, part_size
                ),
            )
            for part_number, part_size in self._iter_part_sizes(file_size)
        ]
        return PresignedTransfer(object_key=object_key, upload_id=upload_id, parts=parts)
