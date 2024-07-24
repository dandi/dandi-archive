from __future__ import annotations

from typing import TYPE_CHECKING, Literal, get_args

from django.db import models

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from dandiapi.zarr.models import ZarrArchive

    from .asset import Asset
    from .dandiset import Dandiset

AuditRecordType = Literal[
    'create_dandiset',
    'change_owners',
    'update_metadata',
    'add_asset',
    'update_asset',
    'remove_asset',
    'create_zarr',
    'upload_zarr_chunks',
    'delete_zarr_chunks',
    'finalize_zarr',
    'unembargo_dandiset',
    'publish_dandiset',
    'delete_dandiset',
]
AUDIT_RECORD_CHOICES = [(t, t) for t in get_args(AuditRecordType)]


class AuditRecord(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    dandiset_id = models.IntegerField()

    # GitHub enforces a 39 character limit on usernames (see, e.g.,
    # https://docs.github.com/en/enterprise-cloud@latest/admin/managing-iam/iam-configuration-reference/username-considerations-for-external-authentication).
    username = models.CharField(max_length=39)

    # According to RFC 5321 (https://www.rfc-editor.org/rfc/rfc5321.txt),
    # section 4.5.3.1.3, an email address "path" is limited to 256 octets,
    # including the surrounding angle brackets. Without the brackets, that
    # leaves 254 characters for the email address itself.
    user_email = models.CharField(max_length=254)

    # The signup questionnaire imposes a 150 character limit on both first and
    # last names; together with a space to separate them, that makes a 301
    # character limit on the full name.
    user_fullname = models.CharField(max_length=301)
    record_type = models.CharField(max_length=32, choices=AUDIT_RECORD_CHOICES)
    details = models.JSONField(blank=True)

    def __str__(self):
        return f'{self.record_type}/{self.dandiset_id:06}'

    @staticmethod
    def make_audit_record(
        *, dandiset: Dandiset, user: User, record_type: AuditRecordType, details: dict
    ) -> AuditRecord:
        return AuditRecord(
            dandiset_id=dandiset.id,
            username=user.username,
            user_email=user.email,
            user_fullname=f'{user.first_name} {user.last_name}',
            record_type=record_type,
            details=details,
        )

    @staticmethod
    def create_dandiset(*, dandiset: Dandiset, user: User, metadata: dict, embargoed: bool):
        details = {
            'metadata': metadata,
            'embargoed': embargoed,
        }
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='create_dandiset', details=details
        )

    @staticmethod
    def change_owners(
        *, dandiset: Dandiset, user: User, removed_owners: list[User], added_owners: list[User]
    ):
        def glean_user_info(user: User):
            return {
                'username': user.username,
                'email': user.email,
                'name': f'{user.first_name} {user.last_name}',
            }

        details = {
            'removed_owners': [glean_user_info(u) for u in removed_owners],
            'added_owners': [glean_user_info(u) for u in added_owners],
        }
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='change_owners', details=details
        )

    @staticmethod
    def update_metadata(*, dandiset: Dandiset, user: User, metadata: dict) -> AuditRecord:
        details = {'metadata': metadata}
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='update_metadata', details=details
        )

    @staticmethod
    def _asset_details(asset: Asset) -> dict:
        checksum = (
            (asset.blob and asset.blob.etag)
            or (asset.embargoed_blob and asset.embargoed_blob.etag)
            or (asset.zarr and asset.zarr.checksum)
        )

        return {
            'path': asset.path,
            'asset_blob_id': asset.blob and asset.blob.id,
            'embargoed_asset_blob_id': asset.embargoed_blob and asset.embargoed_blob.id,
            'zarr_archive_id': asset.zarr and asset.zarr.id,
            'asset_id': asset.id,
            'checksum': checksum,
            'metadata': asset.metadata,
        }

    @staticmethod
    def add_asset(*, dandiset: Dandiset, user: User, asset: Asset) -> AuditRecord:
        details = AuditRecord._asset_details(asset)
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='add_asset', details=details
        )

    @staticmethod
    def update_asset(*, dandiset: Dandiset, user: User, asset: Asset) -> AuditRecord:
        details = AuditRecord._asset_details(asset)
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='update_asset', details=details
        )

    @staticmethod
    def remove_asset(*, dandiset: Dandiset, user: User, asset: Asset) -> AuditRecord:
        details = {
            'path': asset.path,
            'asset_id': asset.id,
        }
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='remove_asset', details=details
        )

    @staticmethod
    def create_zarr(*, dandiset: Dandiset, user: User, zarr_archive: ZarrArchive) -> AuditRecord:
        details = {
            'zarr_id': zarr_archive.id,
            'name': zarr_archive.name,
        }
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='create_zarr', details=details
        )

    @staticmethod
    def upload_zarr_chunks(
        *, dandiset: Dandiset, user: User, zarr_archive: ZarrArchive, paths: list[str]
    ) -> AuditRecord:
        details = {
            'zarr_id': zarr_archive.id,
            'paths': paths,
        }
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='upload_zarr_chunks', details=details
        )

    @staticmethod
    def delete_zarr_chunks(
        *, dandiset: Dandiset, user: User, zarr_archive: ZarrArchive, paths: list[str]
    ) -> AuditRecord:
        details = {
            'zarr_id': zarr_archive.id,
            'paths': paths,
        }
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='delete_zarr_chunks', details=details
        )

    @staticmethod
    def finalize_zarr(*, dandiset: Dandiset, user: User, zarr_archive: ZarrArchive) -> AuditRecord:
        details = {
            'zarr_id': zarr_archive.id,
        }
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='finalize_zarr', details=details
        )

    @staticmethod
    def unembargo_dandiset(*, dandiset: Dandiset, user: User) -> AuditRecord:
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='unembargo_dandiset', details={}
        )

    @staticmethod
    def publish_dandiset(*, dandiset: Dandiset, user: User, version: str) -> AuditRecord:
        details = {
            'version': version,
        }
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='publish_dandiset', details=details
        )

    @staticmethod
    def delete_dandiset(*, dandiset: Dandiset, user: User):
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='delete_dandiset', details={}
        )
