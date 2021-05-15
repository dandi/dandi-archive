"""
Re-save all Versions and Assets to refresh their metadata.

This script should be run after modifying the computed metadata for either Versions or Assets.
Since the computed metadata is only computed when the model is saved, the models need to be
saved to trigger computation.
"""
from dandiapi.api.models import Asset, Version


def run():
    """This is a fairly DANGEROUS operation, since it will operate on
    any asset and version, whether published or not. This script should either
    be removed after the immediate need to update or improved to not operate on
    published assets and dandisets.
    """
    schema_version = "0.3.1"
    for asset in Asset.objects.all():
        asset.metadata.metadata["schemaVersion"] = schema_version
        # This should be checked. I believe asset and version behave differently
        # with respect to when metadata are modified
        asset.metadata.metadata['@context'] = (
            'https://raw.githubusercontent.com/dandi/schema/master/releases/'
            f'{schema_version}/context.json'
        )
        asset.save()

    for version in Version.objects.all():
        version.metadata.metadata["schemaVersion"] = schema_version
        version.save()
