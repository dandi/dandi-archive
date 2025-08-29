# ruff: noqa: PLR0913

from __future__ import annotations

from typing import TYPE_CHECKING

from dandiapi.api.models import AuditRecord, Dandiset

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from dandiapi.api.models.asset import Asset
    from dandiapi.api.models.audit import AuditRecordType
    from dandiapi.zarr.models import ZarrArchive


def _make_audit_record(
    *,
    dandiset: Dandiset,
    user: User | None,
    record_type: AuditRecordType,
    details: dict,
    admin: bool = False,
    description: str = '',
) -> AuditRecord:
    if not admin and user is None:
        raise ValueError('Non-null `user` required when `admin` is False')

    audit_record = AuditRecord(
        dandiset_id=dandiset.id,
        username=user.username if user else '',
        user_email=user.email if user else '',
        user_fullname=f'{user.first_name} {user.last_name}' if user else '',
        record_type=record_type,
        details=details,
        admin=admin,
        description=description,
    )
    audit_record.save()

    return audit_record


def create_dandiset(
    *,
    dandiset: Dandiset,
    user: User | None,
    metadata: dict,
    admin: bool = False,
    description: str = '',
):
    details = {
        'metadata': metadata,
        'embargoed': dandiset.embargo_status == Dandiset.EmbargoStatus.EMBARGOED,
    }
    return _make_audit_record(
        dandiset=dandiset,
        user=user,
        record_type='create_dandiset',
        details=details,
        admin=admin,
        description=description,
    )


def change_owners(
    *,
    dandiset: Dandiset,
    user: User | None,
    removed_owners: list[User],
    added_owners: list[User],
    admin: bool = False,
    description: str = '',
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
        dandiset=dandiset,
        user=user,
        record_type='change_owners',
        details=details,
        admin=admin,
        description=description,
    )


def update_metadata(
    *,
    dandiset: Dandiset,
    user: User | None,
    metadata: dict,
    admin: bool = False,
    description: str = '',
) -> AuditRecord:
    details = {'metadata': metadata}
    return _make_audit_record(
        dandiset=dandiset,
        user=user,
        record_type='update_metadata',
        details=details,
        admin=admin,
        description=description,
    )


def _asset_details(asset: Asset) -> dict:
    checksum = (asset.blob and asset.blob.etag) or (asset.zarr and asset.zarr.checksum)

    return {
        'path': asset.path,
        'asset_blob_id': asset.blob and str(asset.blob.blob_id),
        'zarr_archive_id': asset.zarr and str(asset.zarr.zarr_id),
        'asset_id': str(asset.asset_id),
        'checksum': checksum,
        'metadata': asset.metadata,
    }


def add_asset(
    *,
    dandiset: Dandiset,
    user: User | None,
    asset: Asset,
    admin: bool = False,
    description: str = '',
) -> AuditRecord:
    details = _asset_details(asset)
    return _make_audit_record(
        dandiset=dandiset,
        user=user,
        record_type='add_asset',
        details=details,
        admin=admin,
        description=description,
    )


def update_asset(
    *,
    dandiset: Dandiset,
    user: User | None,
    asset: Asset,
    admin: bool = False,
    description: str = '',
) -> AuditRecord:
    details = _asset_details(asset)
    return _make_audit_record(
        dandiset=dandiset,
        user=user,
        record_type='update_asset',
        details=details,
        admin=admin,
        description=description,
    )


def remove_asset(
    *,
    dandiset: Dandiset,
    user: User | None,
    asset: Asset,
    admin: bool = False,
    description: str = '',
) -> AuditRecord:
    details = {
        'path': asset.path,
        'asset_id': str(asset.asset_id),
    }
    return _make_audit_record(
        dandiset=dandiset,
        user=user,
        record_type='remove_asset',
        details=details,
        admin=admin,
        description=description,
    )


def create_zarr(
    *,
    dandiset: Dandiset,
    user: User | None,
    zarr_archive: ZarrArchive,
    admin: bool = False,
    description: str = '',
) -> AuditRecord:
    details = {
        'zarr_id': str(zarr_archive.zarr_id),
        'name': zarr_archive.name,
    }
    return _make_audit_record(
        dandiset=dandiset,
        user=user,
        record_type='create_zarr',
        details=details,
        admin=admin,
        description=description,
    )


def upload_zarr_chunks(
    *,
    dandiset: Dandiset,
    user: User | None,
    zarr_archive: ZarrArchive,
    paths: list[str],
    admin: bool = False,
    description: str = '',
) -> AuditRecord:
    details = {
        'zarr_id': str(zarr_archive.zarr_id),
        'paths': paths,
    }
    return _make_audit_record(
        dandiset=dandiset,
        user=user,
        record_type='upload_zarr_chunks',
        details=details,
        admin=admin,
        description=description,
    )


def delete_zarr_chunks(
    *,
    dandiset: Dandiset,
    user: User | None,
    zarr_archive: ZarrArchive,
    paths: list[str],
    admin: bool = False,
    description: str = '',
) -> AuditRecord:
    details = {
        'zarr_id': str(zarr_archive.zarr_id),
        'paths': paths,
    }
    return _make_audit_record(
        dandiset=dandiset,
        user=user,
        record_type='delete_zarr_chunks',
        details=details,
        admin=admin,
        description=description,
    )


def finalize_zarr(
    *,
    dandiset: Dandiset,
    user: User | None,
    zarr_archive: ZarrArchive,
    admin: bool = False,
    description: str = '',
) -> AuditRecord:
    details = {
        'zarr_id': str(zarr_archive.zarr_id),
    }
    return _make_audit_record(
        dandiset=dandiset,
        user=user,
        record_type='finalize_zarr',
        details=details,
        admin=admin,
        description=description,
    )


def unembargo_dandiset(
    *, dandiset: Dandiset, user: User | None, admin: bool = False, description: str = ''
) -> AuditRecord:
    return _make_audit_record(
        dandiset=dandiset,
        user=user,
        record_type='unembargo_dandiset',
        details={},
    )


def publish_dandiset(
    *,
    dandiset: Dandiset,
    user: User | None,
    version: str,
    admin: bool = False,
    description: str = '',
) -> AuditRecord:
    details = {
        'version': version,
    }
    return _make_audit_record(
        dandiset=dandiset,
        user=user,
        record_type='publish_dandiset',
        details=details,
        admin=admin,
        description=description,
    )


def delete_dandiset(
    *, dandiset: Dandiset, user: User | None, admin: bool = False, description: str = ''
):
    return _make_audit_record(
        dandiset=dandiset,
        user=user,
        record_type='delete_dandiset',
        details={},
        admin=admin,
        description=description,
    )
