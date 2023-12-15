from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

from dandiapi.api.copy import copy_object_multipart
from dandiapi.api.models import Asset, AssetBlob, Dandiset, Upload, Version
from dandiapi.api.services.asset.exceptions import DandisetOwnerRequiredError
from dandiapi.api.tasks import unembargo_dandiset_task

from .exceptions import AssetNotEmbargoedError, DandisetNotEmbargoedError

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.db.models import QuerySet


def _unembargo_asset(asset: Asset):
    """Unembargo an asset by copying its blob to the public bucket."""
    if not asset.blob.embargoed:
        raise AssetNotEmbargoedError

    # TODO: Replace this with object tag removal
    # Matching AssetBlob doesn't exist, copy blob to public bucket
    # resp = copy_object_multipart(
    #     asset.embargoed_blob.blob.storage,
    #     source_bucket=settings.DANDI_DANDISETS_EMBARGO_BUCKET_NAME,
    #     source_key=asset.embargoed_blob.blob.name,
    #     dest_bucket=settings.DANDI_DANDISETS_BUCKET_NAME,
    #     dest_key=Upload.object_key(
    #         asset.embargoed_blob.blob_id, dandiset=asset.embargoed_blob.dandiset
    #     ),
    # )

    # if resp.etag != asset.embargoed_blob.etag:
    #     raise RuntimeError('ETag mismatch between copied object and original embargoed object')

    # Update blob embargoed flag
    asset.blob.embargoed = False
    asset.blob.save()


def _unembargo_dandiset(dandiset: Dandiset):
    draft_version: Version = dandiset.draft_version
    embargoed_assets: QuerySet[Asset] = draft_version.assets.filter(blob__embargoed=True)

    # Unembargo all assets
    for asset in embargoed_assets.iterator():
        _unembargo_asset(asset)

    # Update draft version metadata
    draft_version.metadata['access'] = [
        {'schemaKey': 'AccessRequirements', 'status': 'dandi:OpenAccess'}
    ]
    draft_version.save()

    # Set access on dandiset
    dandiset.embargo_status = Dandiset.EmbargoStatus.OPEN
    dandiset.save()


def unembargo_dandiset(*, user: User, dandiset: Dandiset):
    """Unembargo a dandiset by copying all embargoed asset blobs to the public bucket."""
    if dandiset.embargo_status != Dandiset.EmbargoStatus.EMBARGOED:
        raise DandisetNotEmbargoedError

    if not user.has_perm('owner', dandiset):
        raise DandisetOwnerRequiredError

    unembargo_dandiset_task.delay(dandiset.id)
