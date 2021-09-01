import djclick as click

from dandiapi.api.models import Asset, Version


@click.command()
@click.option('--assets', is_flag=True, default=False)
@click.option('--versions', is_flag=True, default=False)
def refresh_metadata(assets: bool, versions: bool):
    """
    Re-save all Versions and Assets to refresh their metadata.

    This script should be run after modifying the computed metadata for either Versions or Assets.
    Since the computed metadata is only computed when the model is saved, the models need to be
    saved to trigger computation.
    """
    if assets:
        click.echo('Refreshing asset metadata')
        for asset in Asset.objects.all():
            asset.save()

    if versions:
        click.echo('Refreshing draft version metadata')
        # Only update the metadata for draft versions
        for version in Version.objects.filter(version='draft'):
            version.save()
