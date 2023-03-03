from django.db import transaction
from django.db.models.query import QuerySet

from dandiapi.api.models.asset import Asset
from dandiapi.api.services.metadata import validate_asset_metadata


def _maybe_validate_asset_metadata(asset: Asset):
    """
    Validate asset metadata if a checksum for its blob has already been computed.

    If the checksum isn't there yet, it's the responsibility of the checksum code
    to trigger validation for all assets pointing to its blob.
    """
    # Checksums are necessary for the asset metadata to be validated. For asset blobs, the sha256
    # checksum is required. For zarrs, the zarr checksum is required. In both of these cases, if
    # the checksum is not present, asset metadata is not yet validated, and that validation should
    # be kicked off at the end of their respective checksum calculation tasks.
    if asset.is_zarr:
        if asset.zarr.checksum is None:
            return
    else:
        blob = asset.blob or asset.embargoed_blob
        if blob.sha256 is None:
            return

    # We do not bother to delay this because it should run very quickly.
    validate_asset_metadata(asset=asset)


def bulk_recalculate_asset_metadata(*, assets: QuerySet[Asset]):
    with transaction.atomic():
        for asset in assets.iterator():
            # populates metadata
            asset.save()
