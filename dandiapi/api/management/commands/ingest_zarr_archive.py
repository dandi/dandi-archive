import djclick as click

from dandiapi.api.tasks.zarr import ingest_zarr_archive as _ingest_zarr_archive


@click.command()
@click.argument('zarr_id', type=str)
@click.option('--no-checksum', help="Don't recompute checksums", is_flag=True)
@click.option('--no-size', help="Don't recompute total size", is_flag=True)
@click.option('--no-count', help="Don't recompute total file count", is_flag=True)
@click.option('-f', '--force', help="Force re-ingestion", is_flag=True)
def ingest_zarr_archive(*args, **kwargs):
    _ingest_zarr_archive(*args, **kwargs)
