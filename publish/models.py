from __future__ import annotations

import datetime
import hashlib
import logging
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile
from typing import Optional
import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.core.validators import RegexValidator
from django.db import models

from .girder import GirderClient, GirderError, GirderFile
from .storage import create_s3_storage


logger = logging.getLogger(__name__)


class SelectRelatedManager(models.Manager):
    def __init__(self, *related_fields):
        self.related_fields = related_fields
        super().__init__()

    def get_queryset(self):
        return super().get_queryset().select_related(*self.related_fields)


class Dandiset(models.Model):
    # Don't add beginning and end markers, so this can be embedded in larger regexes
    IDENTIFIER_REGEX = r'\d{6}'
    GIRDER_ID_REGEX = r'[0-9a-f]{24}'

    draft_folder_id = models.CharField(
        max_length=24, validators=[RegexValidator(f'^{GIRDER_ID_REGEX}$')],
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    @property
    def identifier(self) -> Optional[str]:
        return f'{self.id:06}' if self.id else ''

    def __str__(self) -> str:
        return self.identifier

    @classmethod
    def from_girder(cls, draft_folder_id: str, client: GirderClient):
        """
        Return the Dandiset corresponding to a Girder `draft_folder_id`.

        Creates the Dandiset if it does not exist.
        """
        draft_folder = client.get_json(f'folder/{draft_folder_id}')

        dandiset_identifier = draft_folder['name']
        try:
            dandiset_id = int(dandiset_identifier)
        except ValueError:
            raise GirderError(f'Invalid Dandiset identifier in Girder: {dandiset_identifier}')
        try:
            dandiset = Dandiset.objects.get(id=dandiset_id)
        except ObjectDoesNotExist:
            dandiset = Dandiset(id=dandiset_id, draft_folder_id=draft_folder_id)
            dandiset.save()
        else:
            # If the Dandiset existed, sync the draft_folder_id
            if dandiset.draft_folder_id != draft_folder_id:
                raise GirderError(
                    f'Known Dandiset identifer {dandiset.identifier} does not'
                    f'match existing Girder folder id {dandiset.draft_folder_id}'
                )
        return dandiset


def _get_default_version() -> str:
    # This cannot be a lambda, as migrations cannot serialize those
    return Version.make_version()


class Version(models.Model):
    VERSION_REGEX = r'0\.\d{6}\.\d{4}'

    dandiset = models.ForeignKey(Dandiset, related_name='versions', on_delete=models.CASCADE)
    version = models.CharField(
        max_length=13,
        validators=[RegexValidator(f'^{VERSION_REGEX}$')],
        default=_get_default_version,
    )  # TODO: rename this?

    metadata = JSONField(blank=True, default=dict)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['dandiset', 'version']]
        get_latest_by = 'created'
        ordering = ['dandiset', '-version']
        indexes = [
            models.Index(fields=['dandiset', 'version']),
        ]

    # Define custom "objects" first, so it will be the "_default_manager", which is more efficient
    # for many automatically generated queries
    objects = SelectRelatedManager('dandiset')

    def __str__(self) -> str:
        return f'{self.dandiset.identifier}: {self.version}'

    @staticmethod
    def datetime_to_version(time: datetime.datetime) -> str:
        return time.strftime('0.%y%m%d.%H%M')

    @classmethod
    def make_version(cls, dandiset: Dandiset = None) -> str:
        versions: models.Manager = dandiset.versions if dandiset else cls.objects

        time = datetime.datetime.utcnow()
        # increment time until there are no collisions
        while True:
            version = cls.datetime_to_version(time)
            collision = versions.filter(version=version).exists()
            if not collision:
                break
            time += datetime.timedelta(minutes=1)

        return version

    @classmethod
    def from_girder(cls, dandiset: Dandiset, client: GirderClient) -> Version:
        draft_folder = client.get_json(f'folder/{dandiset.draft_folder_id}')

        version = Version(dandiset=dandiset, metadata=draft_folder['meta'])
        version.save()
        return version


def _get_asset_blob_prefix(instance: Asset, filename: str) -> str:
    return f'{instance.version.dandiset.identifier}/{instance.version.version}/{filename}'


class Asset(models.Model):  # TODO: was NwbFile
    UUID_REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
    SHA256_REGEX = r'[0-9a-f]{64}'

    version = models.ForeignKey(
        Version, related_name='assets', on_delete=models.CASCADE
    )  # used to be called dandiset
    uuid = models.UUIDField(unique=True, default=uuid.uuid4)

    path = models.CharField(max_length=512)
    size = models.BigIntegerField()
    sha256 = models.CharField(max_length=64, validators=[RegexValidator(f'^{SHA256_REGEX}$')],)
    metadata = JSONField(blank=True, default=dict)

    blob = models.FileField(
        blank=True,
        storage=create_s3_storage(settings.DANDI_DANDISETS_BUCKET_NAME),
        upload_to=_get_asset_blob_prefix,
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['version', 'path']),
        ]

    # objects = SelectRelatedManager('version__dandiset')

    def __str__(self) -> str:
        return self.path

    @classmethod
    def from_girder(cls, version: Version, girder_file: GirderFile, client: GirderClient) -> Asset:
        sha256_hasher = hashlib.sha256()
        blob_size = 0

        with NamedTemporaryFile('r+b') as local_stream:

            logger.info(f'Downloading file {girder_file.girder_id}')
            with client.iter_file_content(girder_file.girder_id) as file_content_iter:
                for chunk in file_content_iter:
                    sha256_hasher.update(chunk)
                    blob_size += len(chunk)
                    local_stream.write(chunk)
            logger.info(f'Downloaded file {girder_file.girder_id}')

            local_stream.seek(0)
            local_path = Path(local_stream.name)
            sha256 = sha256_hasher.hexdigest()

            try:
                subprocess.check_call(['dandi', 'validate', str(local_path)])
            except subprocess.CalledProcessError:
                # TODO: No validation enforcement now
                pass

            blob = File(file=local_stream, name=girder_file.path.lstrip('/'),)
            # content_type is not part of the base File class (it on some other subclasses),
            # but regardless S3Boto3Storage will respect and use it, if it's set
            blob.content_type = 'application/octet-stream'

            # s3.put_object(
            #     Bucket=S3_BUCKET,
            #     Key=f'{prefix}/dandiset.yaml',
            #     Body=dump(self.metadata['dandiset']).encode(),
            #     ACL='public-read',
            # )

            asset = Asset(
                version=version,
                path=girder_file.path,
                size=blob_size,
                sha256=sha256,
                metadata=girder_file.metadata,
                blob=blob,
            )
            # The actual upload of blob occurs when the asset is saved
            asset.save()
        return asset
