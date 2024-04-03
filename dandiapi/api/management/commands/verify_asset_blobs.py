from __future__ import annotations

import json

import djclick as click
from tqdm import tqdm

from dandiapi.api.models import AssetBlob


@click.command()
@click.argument('file')
def migrate_published_version_metadata(*, file: str):
    with open(file) as f:  # noqa: PTH123
        old_blobs = json.load(f)

    not_found = []
    for blob in tqdm(old_blobs):
        migrated = AssetBlob.objects.filter(
            etag=blob['etag'], size=blob['size'], download_count__gte=blob['download_count']
        )
        if not migrated.exists():
            not_found.append(blob)

    if not_found:
        click.echo(json.dumps(not_found, indent=2))
        click.echo(f"Couldn't find {len(not_found)} blobs")
    else:
        click.echo(click.style('All asset blobs verified', fg='green'))
