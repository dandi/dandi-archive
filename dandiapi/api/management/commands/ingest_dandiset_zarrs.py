import djclick as click

from dandiapi.api.tasks.zarr import ingest_dandiset_zarrs as _ingest_dandiset_zarrs


@click.command()
@click.argument('dandiset_id', type=str)
@click.option('--no-checksum', help="Don't recompute checksums", is_flag=True)
@click.option('--no-size', help="Don't recompute total size", is_flag=True)
@click.option('--no-count', help="Don't recompute total file count", is_flag=True)
@click.option('-f', '--force', help="Force re-ingestion", is_flag=True)
def ingest_dandiset_zarrs(dandiset_id: str, **kwargs):
    _ingest_dandiset_zarrs(dandiset_id=int(dandiset_id.lstrip('0')), **kwargs)
