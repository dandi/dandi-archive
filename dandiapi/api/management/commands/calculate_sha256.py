from __future__ import annotations

import djclick as click

from dandiapi.api.models import Asset
from dandiapi.api.tasks import calculate_sha256 as do_calculate_sha256


@click.command()
@click.option('--blob-id', 'blob_id', help='Blob ID')
@click.option('--asset-id', 'asset_id', help='Asset ID')
def calculate_sha256(asset_id: str | None = None, blob_id: str | None = None):
    """Trigger computation of sha256 for a blob.

    Either blob-id or asset-id should be provided.
    """
    # Handle mutually exclusive option failure cases.
    if not asset_id and not blob_id:
        raise ValueError('Provide either asset_id or blob_id')
    if asset_id and blob_id:
        raise ValueError('Provide only asset_id or blob_id, not both')

    # Make sure we have a good blob_id to work with.
    if asset_id:
        asset = Asset.objects.get(asset_id=asset_id)
        blob_id = asset.blob_id

    do_calculate_sha256(blob_id=blob_id)
