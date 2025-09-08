from __future__ import annotations

import hashlib
import io
import json
from typing import TYPE_CHECKING, Any
from urllib.parse import ParseResult, urlencode

from botocore.config import Config
from botocore.exceptions import ClientError
from storages.backends.s3 import S3Storage
from storages.utils import clean_name

if TYPE_CHECKING:
    from collections.abc import Mapping

    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_s3.service_resource import S3ServiceResource


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
            # Also set by AWS_S3_SIGNATURE_VERSION, but it's critical, so ensure it's set here
            signature_version='s3v4',
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
        # TODO: Remove this method once https://github.com/jschneier/django-storages/pull/1536
        #  is released.
        name = self._normalize_name(clean_name(name))
        if self.endpoint_url:
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
        name = self._normalize_name(clean_name(name))
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
        # TODO: Remove this method once https://github.com/jschneier/django-storages/pull/1533
        #  is released.
        name = self._normalize_name(clean_name(name))
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
        name = self._normalize_name(clean_name(name))
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
        name = self._normalize_name(clean_name(name))
        return {
            tag['Key']: tag['Value']
            for tag in self.s3_client.get_object_tagging(Bucket=self.bucket_name, Key=name)[
                'TagSet'
            ]
        }

    def put_tags(self, name: str, tags: Mapping[str, str]) -> None:
        name = self._normalize_name(clean_name(name))
        self.s3_client.put_object_tagging(
            Bucket=self.bucket_name,
            Key=name,
            Tagging={'TagSet': [{'Key': key, 'Value': value} for key, value in tags.items()]},
        )

    def delete_tags(self, name: str) -> None:
        name = self._normalize_name(clean_name(name))
        self.s3_client.delete_object_tagging(Bucket=self.bucket_name, Key=name)

    def sha256_checksum(self, name: str) -> str:
        """Efficiently compute the SHA256 checksum of an object."""
        name = self._normalize_name(clean_name(name))
        hasher = _WritableSha256()
        s3_object = self.bucket.Object(name)
        s3_object.download_fileobj(hasher)
        return hasher.hexdigest()


class MinioDandiS3Storage(DandiS3Storage):
    """Storage to be used for local development with MinIO."""

    def __init__(self, media_url: ParseResult | None = None, **settings):
        super().__init__(
            # This is MinIO's default region
            region_name='us-east-1',
            **settings,
        )

        self.media_url = media_url

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

    @property
    def media_connection(self) -> S3ServiceResource:
        """
        Represents the direct network connection from an end user to S3/MinIO.

        Particularly due to Docker, this may use a different hostname.
        """
        if not self.media_url:
            raise ValueError('media_url must be set')
        media_connection = getattr(self._connections, 'media_connection', None)
        if media_connection is None:
            session = self._create_session()
            self._connections.media_connection = session.resource(
                's3',
                region_name=self.region_name,
                use_ssl=self.media_url.scheme == 'https',
                endpoint_url=f'{self.media_url.scheme}://{self.media_url.hostname}:{self.media_url.port}',
                config=self.client_config,
                verify=False,
            )
        return self._connections.media_connection

    def _url_unsigned(self, name: str) -> str:
        if self.media_url:
            name = self._normalize_name(clean_name(name))
            return f'{self.media_url.scheme}://{self.media_url.hostname}:{self.media_url.port}/{self.bucket_name}/{name}'
        return super()._url_unsigned(name)

    def url(
        self,
        name: str,
        *,
        parameters: Mapping[str, Any] | None = None,
        expire: int | None = None,
        http_method: str | None = None,
        signed: bool = True,
    ) -> str:
        if self.media_url:
            if signed:
                name = self._normalize_name(clean_name(name))
                if parameters is None:
                    parameters = {}
                if expire is None:
                    expire = self.querystring_expire

                return self.media_connection.meta.client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket.name,
                        'Key': name,
                        **parameters,
                    },
                    ExpiresIn=expire,
                    HttpMethod=http_method,
                )
            return self._url_unsigned(name)
        return super().url(
            name, parameters=parameters, expire=expire, http_method=http_method, signed=signed
        )

    def generate_presigned_put_object_url(
        self,
        name: str,
        *,
        expire: int | None = None,
        content_md5: str | None = None,
        tags: Mapping[str, str] | None = None,
    ) -> str:
        if self.media_url:
            name = self._normalize_name(clean_name(name))
            if expire is None:
                expire = self.querystring_expire
            optional_params = {}
            if content_md5 is not None:
                optional_params['ContentMD5'] = content_md5
            if tags is not None:
                optional_params['Tagging'] = urlencode(tags)

            return self.media_connection.meta.client.generate_presigned_url(
                ClientMethod='put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': name,
                    **optional_params,
                },
                ExpiresIn=expire,
            )
        return super().generate_presigned_put_object_url(
            name, expire=expire, content_md5=content_md5, tags=tags
        )
