from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import QuerySet

from dandiapi.api.copy import copy_object_multipart
from dandiapi.api.models import Asset, AssetBlob, Dandiset, Upload, Version
from dandiapi.api.services.asset.exceptions import DandisetOwnerRequired
from dandiapi.api.tasks import unembargo_dandiset_task

from .exceptions import AssetNotEmbargoed, DandisetNotEmbargoed


def _unembargo_asset(asset: Asset):
    """Unembargo an asset by copying its blob to the public bucket."""
    if asset.embargoed_blob is None:
        raise AssetNotEmbargoed()

    # Use existing AssetBlob if possible
    etag = asset.embargoed_blob.etag
    matching_blob = AssetBlob.objects.filter(etag=etag).first()
    if matching_blob is not None:
        asset.blob = matching_blob
    else:
        # Matching AssetBlob doesn't exist, copy blob to public bucket
        resp = copy_object_multipart(
            asset.embargoed_blob.blob.storage,
            source_bucket=settings.DANDI_DANDISETS_EMBARGO_BUCKET_NAME,
            source_key=asset.embargoed_blob.blob.name,
            dest_bucket=settings.DANDI_DANDISETS_BUCKET_NAME,
            dest_key=Upload.object_key(
                asset.embargoed_blob.blob_id, dandiset=asset.embargoed_blob.dandiset
            ),
        )

        # Assert files are equal
        assert resp.etag == asset.embargoed_blob.etag

        # Assign blob (changing only blob)
        asset.blob = AssetBlob(
            blob=resp.key,
            blob_id=asset.embargoed_blob.blob_id,
            sha256=asset.embargoed_blob.sha256,
            etag=asset.embargoed_blob.etag,
            size=asset.embargoed_blob.size,
        )
        asset.blob.save()

    # Save updated blob field
    # TODO: Use select_for_update?
    asset.embargoed_blob = None
    asset.metadata = asset._populate_metadata()
    asset.save()


def _unembargo_dandiset(dandiset: Dandiset):
    draft_version: Version = dandiset.draft_version
    embargoed_assets: QuerySet[Asset] = draft_version.assets.filter(embargoed_blob__isnull=False)

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
        raise DandisetNotEmbargoed

    if not user.has_perm('owner', dandiset):
        raise DandisetOwnerRequired()

    unembargo_dandiset_task.delay(dandiset.id)
