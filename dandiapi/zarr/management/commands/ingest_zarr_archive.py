from __future__ import annotations

import djclick as click

from dandiapi.zarr.tasks import ingest_zarr_archive as _ingest_zarr_archive


@click.command()
@click.argument('zarr_id', type=str)
@click.option('-f', '--force', help='Force re-ingestion', is_flag=True)
def ingest_zarr_archive(*args, **kwargs):
    _ingest_zarr_archive(*args, **kwargs)
