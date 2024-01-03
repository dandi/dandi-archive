from __future__ import annotations
import djclick as click

from dandiapi.zarr.tasks import ingest_dandiset_zarrs as _ingest_dandiset_zarrs


@click.command()
@click.argument('dandiset_id', type=str)
@click.option('-f', '--force', help='Force re-ingestion', is_flag=True)
def ingest_dandiset_zarrs(*, dandiset_id: str, **kwargs):
    _ingest_dandiset_zarrs(dandiset_id=int(dandiset_id.lstrip('0')), **kwargs)
