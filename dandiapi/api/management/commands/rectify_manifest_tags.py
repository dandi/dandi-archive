from __future__ import annotations

import logging

from django.core.files.storage import default_storage
import djclick as click

from dandiapi.api.manifests import all_manifest_filepaths
from dandiapi.api.models import Version
from dandiapi.api.models.dandiset import Dandiset

logger = logging.getLogger(__name__)


@click.command()
@click.argument(
    'dandisets',
    type=click.INT,
    nargs=-1,
)
@click.option(
    '-a',
    '--all',
    'include_all',
    is_flag=True,
    help='Run on all dandisets.',
)
def tag_embargoed_manifests(dandisets, include_all):
    """Apply embargoed tags to dandiset manifest files."""
    if bool(dandisets) == include_all:
        raise click.ClickException("Must specify exactly one of 'dandisets' or --all")

    embargoed_versions = Version.objects.select_related('dandiset').filter(
        dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED, version='draft'
    )
    if dandisets:
        embargoed_versions = embargoed_versions.filter(dandiset_id__in=dandisets)

    for version in embargoed_versions:
        logger.info('Adding tags from dandiset %s', version.dandiset.identifier)
        paths = all_manifest_filepaths(version)
        for path in paths:
            try:
                existing_tags: dict[str, str] = default_storage.get_tags(path)
                filtered_tags = {
                    key: val for key, val in existing_tags.items() if key != 'embargoed'
                }
                new_tags = {**filtered_tags, 'embargoed': 'true'}
                default_storage.put_tags(path, new_tags)
            except default_storage.s3_client.exceptions.NoSuchKey:
                logger.info('\tManifest file not found at %s. Continuing...', path)
                continue
