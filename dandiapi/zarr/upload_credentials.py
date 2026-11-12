from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.conf import settings

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from dandiapi.storage import TemporaryCredentials
    from dandiapi.zarr.models import ZarrArchive


def required_object_tags(zarr_archive: ZarrArchive) -> dict[str, str]:
    """Return the tags which must be set on every object uploaded to a zarr archive."""
    if zarr_archive.embargoed:
        return {'embargoed': 'true'}
    return {}


def upload_session_policy(zarr_archive: ZarrArchive) -> dict[str, Any]:
    """
    Build the IAM session policy for credentials that upload to a zarr archive.

    The policy only allows objects under the zarr archive's own prefix to be written and deleted.
    For an embargoed zarr archive, every write must set the "embargoed" tag; otherwise, that tag
    must never be set.
    """
    resource = f'arn:aws:s3:::{zarr_archive.storage.bucket_name}/{zarr_archive.s3_path("")}*'

    put_statement: dict[str, Any]
    if zarr_archive.embargoed:
        put_statement = {
            'Effect': 'Allow',
            # S3 requires "s3:PutObjectTagging" in addition to "s3:PutObject", for an upload that
            # sets tags. This also allows the tags of an existing object to be replaced, but the
            # condition applies there too, so the "embargoed" tag can't be removed that way.
            'Action': ['s3:PutObject', 's3:PutObjectTagging'],
            'Resource': resource,
            'Condition': {'StringEquals': {'s3:RequestObjectTag/embargoed': 'true'}},
        }
    else:
        put_statement = {
            'Effect': 'Allow',
            'Action': 's3:PutObject',
            'Resource': resource,
            'Condition': {'Null': {'s3:RequestObjectTag/embargoed': 'true'}},
        }

    return {
        'Version': '2012-10-17',
        'Statement': [
            put_statement,
            {
                'Effect': 'Allow',
                # This does not include "s3:DeleteObjectVersion", so deletions remain recoverable
                'Action': 's3:DeleteObject',
                'Resource': resource,
            },
        ],
    }


def issue_upload_credentials(*, zarr_archive: ZarrArchive, user: User) -> TemporaryCredentials:
    """Issue temporary S3 credentials that can only upload to a single zarr archive."""
    if settings.DANDI_ZARR_UPLOAD_ROLE_ARN is None:
        raise ValueError('DANDI_ZARR_UPLOAD_ROLE_ARN is not set')

    return zarr_archive.storage.assume_role(
        settings.DANDI_ZARR_UPLOAD_ROLE_ARN,
        # The session name is recorded in S3 access logs, attributing each object operation
        session_name=f'u{user.pk}-z{zarr_archive.zarr_id}',
        policy=upload_session_policy(zarr_archive),
        duration=settings.DANDI_ZARR_UPLOAD_CREDENTIALS_DURATION,
    )
