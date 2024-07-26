from __future__ import annotations

from typing import TYPE_CHECKING

from dandiapi.api.models.audit import AuditRecord

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from dandiapi.api.models.asset import Asset
    from dandiapi.api.models.audit import AuditRecordType
    from dandiapi.api.models.dandiset import Dandiset
    from dandiapi.zarr.models import ZarrArchive


def _make_audit_record(
    *, dandiset: Dandiset, user: User, record_type: AuditRecordType, details: dict
) -> AuditRecord:
    audit_record = AuditRecord(
        dandiset_id=dandiset.id,
        username=user.username,
        user_email=user.email,
        user_fullname=f'{user.first_name} {user.last_name}',
        record_type=record_type,
        details=details,
    )
    audit_record.save()

    return audit_record


def create_dandiset(*, dandiset: Dandiset, user: User, metadata: dict, embargoed: bool):
    details = {
        'metadata': metadata,
        'embargoed': embargoed,
    }
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='create_dandiset', details=details
    )


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
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='change_owners', details=details
    )


def update_metadata(*, dandiset: Dandiset, user: User, metadata: dict) -> AuditRecord:
    details = {'metadata': metadata}
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='update_metadata', details=details
    )


def _asset_details(asset: Asset) -> dict:
    checksum = (asset.blob and asset.blob.etag) or (asset.zarr and asset.zarr.checksum)

    return {
        'path': asset.path,
        'asset_blob_id': asset.blob and asset.blob.id,
        'zarr_archive_id': asset.zarr and asset.zarr.id,
        'asset_id': asset.id,
        'checksum': checksum,
        'metadata': asset.metadata,
    }


def add_asset(*, dandiset: Dandiset, user: User, asset: Asset) -> AuditRecord:
    details = _asset_details(asset)
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='add_asset', details=details
    )


def update_asset(*, dandiset: Dandiset, user: User, asset: Asset) -> AuditRecord:
    details = _asset_details(asset)
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='update_asset', details=details
    )


def remove_asset(*, dandiset: Dandiset, user: User, asset: Asset) -> AuditRecord:
    details = {
        'path': asset.path,
        'asset_id': asset.id,
    }
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='remove_asset', details=details
    )


def create_zarr(*, dandiset: Dandiset, user: User, zarr_archive: ZarrArchive) -> AuditRecord:
    details = {
        'zarr_id': zarr_archive.id,
        'name': zarr_archive.name,
    }
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='create_zarr', details=details
    )


def upload_zarr_chunks(
    *, dandiset: Dandiset, user: User, zarr_archive: ZarrArchive, paths: list[str]
) -> AuditRecord:
    details = {
        'zarr_id': zarr_archive.id,
        'paths': paths,
    }
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='upload_zarr_chunks', details=details
    )


def delete_zarr_chunks(
    *, dandiset: Dandiset, user: User, zarr_archive: ZarrArchive, paths: list[str]
) -> AuditRecord:
    details = {
        'zarr_id': zarr_archive.id,
        'paths': paths,
    }
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='delete_zarr_chunks', details=details
    )


def finalize_zarr(*, dandiset: Dandiset, user: User, zarr_archive: ZarrArchive) -> AuditRecord:
    details = {
        'zarr_id': zarr_archive.id,
    }
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='finalize_zarr', details=details
    )


def unembargo_dandiset(*, dandiset: Dandiset, user: User) -> AuditRecord:
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='unembargo_dandiset', details={}
    )


def publish_dandiset(*, dandiset: Dandiset, user: User, version: str) -> AuditRecord:
    details = {
        'version': version,
    }
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='publish_dandiset', details=details
    )


def delete_dandiset(*, dandiset: Dandiset, user: User):
    return _make_audit_record(
        dandiset=dandiset, user=user, record_type='delete_dandiset', details={}
    )
