from __future__ import annotations

import json

import djclick as click

from dandiapi.api.models.asset import EmbargoedAssetBlob


@click.command()
def generate():
    embargoed_blobs = list(
        EmbargoedAssetBlob.objects.values(
            'blob',
            'blob_id',
            'etag',
            'size',
            'sha256',
            'download_count',
            'dandiset',
        )
    )

    with open('BLOBS.json', 'w') as _out:  # noqa: PTH123
        json.dump(embargoed_blobs, _out, indent=2, default=str)
