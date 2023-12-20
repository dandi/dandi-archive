from __future__ import annotations

from django.db import transaction
import djclick as click

from dandiapi.zarr.models import ZarrArchive


@click.command()
@click.argument('dandiset_id', type=int, required=False)
def rename_ngff(*, dandiset_id: int | None):
    """
    Change extension of all .ngff ZarrArchives (plus their associated Asset paths) to .ome.zarr.

    If DANDISET_ID is provided, only ZarrArchives in that dandiset will be modified.
    Otherwise, every ZarrArchive in the DB is modified.
    """
    qs = ZarrArchive.objects.filter(name__endswith='.ngff')

    # If a dandiset id was provided, filter by that.
    if dandiset_id is not None:
        click.echo(f'Renaming .ngff files to .ome.zarr for dandiset {dandiset_id}...')
        qs = qs.filter(dandiset_id=dandiset_id)
    else:
        click.echo('Renaming .ngff files to .ome.zarr for all dandisets...')

    for zarr in qs.prefetch_related('assets'):
        new_name = f'{zarr.name[:-5]}.ome.zarr'

        # only rename the ngff if a ome.zarr hasn't been uploaded already
        if not ZarrArchive.objects.filter(name=new_name, dandiset=zarr.dandiset).exists():
            click.echo(f'Renaming ZarrArchive ({zarr.id}) from {zarr.name} to {new_name}.')
            with transaction.atomic():
                zarr.name = new_name
                zarr.save(update_fields=['name'])

                for asset in zarr.assets.iterator():
                    if asset.path.endswith('.ngff'):
                        new_path = f'{asset.path[:-5]}.ome.zarr'
                        click.echo(
                            f'  Renaming Asset ({asset.id}) path from {asset.path} to {new_path}.'
                        )
                        asset.path = new_path
                        asset.save(update_fields=['path'])
