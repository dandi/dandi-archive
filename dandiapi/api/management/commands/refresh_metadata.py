import djclick as click

from dandiapi.api.models import Asset, Version


@click.command()
def refresh_metadata():
    """
    Re-save all Versions and Assets to refresh their metadata.

    This script should be run after modifying the computed metadata for either Versions or Assets.
    Since the computed metadata is only computed when the model is saved, the models need to be
    saved to trigger computation.
    """
    for asset in Asset.objects.all():
        asset.save()

    for version in Version.objects.all():
        version.save()
