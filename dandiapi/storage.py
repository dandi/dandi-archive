from __future__ import annotations

import hashlib
import io
import json
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from botocore.config import Config
from botocore.exceptions import ClientError
from storages.backends.s3 import S3Storage

if TYPE_CHECKING:
    from collections.abc import Mapping

    from mypy_boto3_s3.client import S3Client


class _WritableSha256(io.RawIOBase):
    """File-like object that calculates the SHA256 of everything written to it."""

    def __init__(self):
        self._hasher = hashlib.sha256()

    def write(self, data: bytes) -> int:
        self._hasher.update(data)
        return len(data)

    def hexdigest(self) -> str:
        return self._hasher.hexdigest()

    def writable(self) -> bool:
        return True


class DandiS3Storage(S3Storage):
    """
    An enhanced S3Storage.

    This class additionally:
    * Does not transform original filenames
    * Allows unsigned URLs to be generated
    * Provides an API to generate presigned PUT URLs
    * Provides an API to get the ETag of an object
    * Provides an API to tag objects
    * Provides an API to efficiently calculate the SHA256 checksums of an object
    """

    # S3Storage provides this, but doesn't properly annotate it
    bucket_name: str

    def __init__(self, **settings):
        super().__init__(
            client_config=Config(
                signature_version='s3v4',
                # These settings are not available in upstream S3Storage
                connect_timeout=5,
                read_timeout=5,
                retries={
                    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html#standard-retry-mode
                    'mode': 'standard',
                },
            ),
            **settings,
        )

    @property
    def s3_client(self) -> S3Client:
        return self.connection.meta.client

    # The basic S3Storage does not implement generate_filename or get_valid_name,
    # so upon FileField save, the following call stack normally occurs:
    #   FieldFile.save
    #   FileField.generate_filename
    #   Storage.generate_filename
    #   Storage.get_valid_name
    # Storage.generate_filename attempts to normalize the filename as a path.
    # Storage.get_valid_name uses django.utils.text.get_valid_filename,
    # which cleans spaces and other characters.
    # Since these are designed around filesystem safety, not S3 key safety, it's
    # simpler to do sanitization before saving.
    def generate_filename(self, filename: str) -> str:
        return filename

    def _url_unsigned(self, name: str) -> str:
        if self.endpoint_url:
            # TODO: correct URL when inside Docker
            # Assume only path-style requests are supported, as this is probably MinIO
            return f'{self.endpoint_url}/{self.bucket_name}/{name}'
        # https://docs.aws.amazon.com/AmazonS3/latest/userguide/VirtualHosting.html#virtual-hosted-style-access
        return f'https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{name}'

    def url(
        self,
        name: str,
        *,
        parameters: Mapping[str, Any] | None = None,
        expire: int | None = None,
        http_method: str | None = None,
        signed: bool = True,
    ) -> str:
        if signed:
            return super().url(name, parameters=parameters, expire=expire, http_method=http_method)
        return self._url_unsigned(name)

    def generate_presigned_put_object_url(
        self,
        name: str,
        *,
        expire: int | None = None,
        content_md5: str | None = None,
        tags: Mapping[str, str] | None = None,
    ) -> str:
        # Just calling "S3Storage.url(..., http_method=='PUT')" doesn't work, as "get_object" can't
        # accept "Tagging" options, even if its method is overridden.
        if expire is None:
            expire = self.querystring_expire
        optional_params = {}
        if content_md5 is not None:
            optional_params['ContentMD5'] = content_md5
        if tags is not None:
            optional_params['Tagging'] = urlencode(tags)

        return self.connection.meta.client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': name,
                **optional_params,
            },
            ExpiresIn=expire,
        )

    def e_tag(self, name: str) -> str | None:
        """Return the ETag (entity tag) for an uploaded object, or `None` if it's unavailable."""
        try:
            e_tag = self.bucket.Object(name).e_tag
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            raise
        # S3 wraps the ETag in double quotes
        return e_tag.strip('"')

    def get_tags(self, name: str) -> dict[str, str]:
        return {
            tag['Key']: tag['Value']
            for tag in self.s3_client.get_object_tagging(Bucket=self.bucket_name, Key=name)[
                'TagSet'
            ]
        }

    def put_tags(self, name: str, tags: Mapping[str, str]) -> None:
        self.s3_client.put_object_tagging(
            Bucket=self.bucket_name,
            Key=name,
            Tagging={'TagSet': [{'Key': key, 'Value': value} for key, value in tags.items()]},
        )

    def delete_tags(self, name: str) -> None:
        self.s3_client.delete_object_tagging(Bucket=self.bucket_name, Key=name)

    def sha256_checksum(self, name: str) -> str:
        """Efficiently compute the SHA256 checksum of an object."""
        hasher = _WritableSha256()
        s3_object = self.bucket.Object(name)
        s3_object.download_fileobj(hasher)
        return hasher.hexdigest()


class MinioDandiS3Storage(DandiS3Storage):
    """Storage to be used for local development with MinIO."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self._bucket_exists():
            self._create_bucket()

    def _bucket_exists(self) -> bool:
        try:
            self.bucket.meta.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
        return True

    def _create_bucket(self) -> None:
        self.bucket.create()
        self.bucket.Policy().put(
            Policy=json.dumps(
                {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'AWS': ['*']},
                            'Action': ['s3:GetBucketLocation'],
                            'Resource': [f'arn:aws:s3:::{self.bucket_name}'],
                        },
                        {
                            'Effect': 'Allow',
                            'Principal': {'AWS': ['*']},
                            'Action': ['s3:ListBucket'],
                            'Resource': [f'arn:aws:s3:::{self.bucket_name}'],
                        },
                        {
                            'Effect': 'Allow',
                            'Principal': {'AWS': ['*']},
                            'Action': ['s3:GetObject'],
                            'Resource': [f'arn:aws:s3:::{self.bucket_name}/*'],
                        },
                    ],
                }
            )
        )
