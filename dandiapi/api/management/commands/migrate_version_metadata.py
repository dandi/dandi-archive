from __future__ import annotations

import logging

from dandischema.metadata import migrate
from django.db import transaction
import djclick as click

from dandiapi.api.models import Version
from dandiapi.api.services import audit
from dandiapi.api.services.metadata import validate_version_metadata

logger = logging.getLogger(__name__)


@click.command()
@click.argument(
    'dandisets',
    type=click.INT,
    nargs=-1,
)
@click.option(
    '--target', 'target_version', default='', help='The target dandischema version to migrate to.'
)
@click.option(
    '-a',
    '--all',
    'include_all',
    is_flag=True,
    help='Run on all dandisets.',
)
def migrate_version_metadata(dandisets: tuple[int, ...], *, include_all: bool, target_version: str):
    if bool(dandisets) == include_all:
        raise click.ClickException("Must specify exactly one of 'dandisets' or --all")
    if not target_version:
        raise click.ClickException('Must specify target schema version via --target')

    versions = Version.objects.filter(version='draft')
    if dandisets:
        versions = versions.filter(dandiset_id__in=dandisets)

    logger.info(
        'Migrating %s dandiset draft versions to schema version %s',
        versions.count(),
        target_version,
    )

    migrated_count = 0
    failed_count = 0
    unchanged_count = 0
    for version in versions.iterator():
        logger.info('-----------------------------------------')
        logger.info('Migrating %s', version)

        with transaction.atomic():
            locked_version = Version.objects.select_for_update().get(id=version.id)

            try:
                metanew = migrate(
                    locked_version.metadata, to_version=target_version, skip_validation=True
                )
                # We set this manually due to https://github.com/dandi/dandi-schema/issues/353
                metanew['schemaVersion'] = target_version
            except Exception as e:
                logger.exception('Failed to migrate %s', version, exc_info=e)
                failed_count += 1
                continue

            if locked_version.metadata == metanew:
                logger.info('No change in metadata for %s. Skipping save...', version)
                unchanged_count += 1
                continue

            version.metadata = metanew
            version.status = Version.Status.PENDING
            version.save()

            audit.update_metadata(
                dandiset=locked_version.dandiset,
                metadata=locked_version.metadata,
                user=None,
                admin=True,
                description=f'Update schema version to {target_version}',
            )

            migrated_count += 1
            logger.info('Metadata migrated for version %s', version)

        # Validate outside of transaction, since this function uses `select_for_update` itself
        validate_version_metadata(version=version)

    logger.info(
        '%d migrated, %d failed, %d left unchanged, out of %d total selected versions',
        migrated_count,
        failed_count,
        unchanged_count,
        versions.count(),
    )
