"""
Re-save all Versions and Assets to refresh their metadata.

This script should be run after modifying the computed metadata for either Versions or Assets.
Since the computed metadata is only computed when the model is saved, the models need to be
saved to trigger computation.
"""
from dandiapi.api.models import Asset, Version


def run():
    for asset in Asset.objects.all():
        asset.save()

    for version in Version.objects.all():
        version.save()
