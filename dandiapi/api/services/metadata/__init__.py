from __future__ import annotations

from typing import TYPE_CHECKING

from celery.utils.log import get_task_logger
from dandischema.conf import get_instance_config as get_schema_instance_config
import dandischema.exceptions
from dandischema.metadata import aggregate_assets_summary, validate
from django.conf import settings
from django.db import transaction
from django.db.models.query_utils import Q
from django.utils import timezone

from dandiapi.api.models import Asset, Version
from dandiapi.api.services.metadata.exceptions import (
    AssetHasBeenPublishedError,
    VersionHasBeenPublishedError,
    VersionMetadataConcurrentlyModifiedError,
)
from dandiapi.api.services.publish import _build_publishable_version_from_draft

if TYPE_CHECKING:
    import jsonschema.exceptions

logger = get_task_logger(__name__)


def _encode_pydantic_error(error) -> dict[str, str]:
    return {'field': error['loc'][0], 'message': error['msg']}


def _encode_jsonschema_error(error: jsonschema.exceptions.ValidationError) -> dict[str, str]:
    return {'field': '.'.join([str(p) for p in error.path]), 'message': error.message}


def _collect_validation_errors(
    error: dandischema.exceptions.ValidationError,
) -> list[dict[str, str]]:
    if type(error) is dandischema.exceptions.PydanticValidationError:
        encoder = _encode_pydantic_error
    elif type(error) is dandischema.exceptions.JsonschemaValidationError:
        encoder = _encode_jsonschema_error
    else:
        raise error
    return [encoder(error) for error in error.errors]


def validate_asset_metadata(*, asset: Asset) -> bool:
    logger.info('Validating asset metadata for asset %s', asset.id)

    # Published assets are immutable
    if asset.published:
        raise AssetHasBeenPublishedError

    # track the state of the asset before to use optimistic locking
    asset_state = asset.status

    with transaction.atomic():
        try:
            metadata = asset.published_metadata()
            validate(metadata, schema_key='PublishedAsset', json_validation=True)
            logger.info('Successfully validated asset %s', asset.id)
            asset.status = Asset.Status.VALID
            asset.validation_errors = []
        except dandischema.exceptions.ValidationError as e:
            logger.info('Error while validating asset %s', asset.id)
            asset.status = Asset.Status.INVALID

            validation_errors = _collect_validation_errors(e)
            asset.validation_errors = validation_errors
        except ValueError as e:
            # A bare ValueError is thrown when dandischema generates its own exceptions, like a
            # mismatched schemaVersion.
            asset.status = Asset.Status.INVALID
            asset.validation_errors = [{'field': '', 'message': str(e)}]

        updated_asset = Asset.objects.filter(
            id=asset.id, status=asset_state, metadata=asset.metadata, published=False
        ).update(status=asset.status, validation_errors=asset.validation_errors)
        if updated_asset:
            # Update modified timestamps on all draft versions this asset belongs to
            asset.versions.filter(version='draft').update(modified=timezone.now())
        else:
            logger.info('Asset %s was modified while validating', asset.id)

        return updated_asset


def version_aggregate_assets_summary(version: Version) -> None:
    if version.version != 'draft':
        raise VersionHasBeenPublishedError

    assets_summary = aggregate_assets_summary(
        asset.full_metadata
        for asset in version.assets.filter(status=Asset.Status.VALID)
        .select_related('blob', 'zarr', 'zarr__dandiset')
        .iterator()
    )

    updated_metadata = {**version.metadata, 'assetsSummary': assets_summary}

    updated_count = Version.objects.filter(id=version.id, metadata=version.metadata).update(
        modified=timezone.now(), metadata=updated_metadata
    )
    if updated_count == 0:
        logger.info('Skipped updating assetsSummary for version %s', version.id)
        raise VersionMetadataConcurrentlyModifiedError


def validate_version_metadata(*, version: Version) -> None:
    def _build_validatable_version_metadata(version: Version) -> dict:
        # since Version.Status.VALID is a proxy for a version being publishable, we need to
        # validate against the PublishedDandiset schema even though we lack several things
        # at validation time: id, url, doi, and assetsSummary. this tricks the validator into
        # giving us the useful errors we need but ignoring the other errors we can't satisfy yet.
        publishable_version = _build_publishable_version_from_draft(version)
        metadata_for_validation = publishable_version.metadata

        metadata_for_validation['id'] = (
            f'{get_schema_instance_config().instance_name}:'
            f'{publishable_version.dandiset.identifier}/{publishable_version.version}'
        )
        metadata_for_validation['url'] = (
            f'{settings.DANDI_WEB_APP_URL}/dandiset/'
            f'{publishable_version.dandiset.identifier}/{publishable_version.version}'
        )
        metadata_for_validation['doi'] = '10.80507/dandi.123456/0.123456.1234'
        metadata_for_validation['assetsSummary'] = {
            'schemaKey': 'AssetsSummary',
            'numberOfBytes': 1
            if version.assets.filter(Q(blob__size__gt=0) | Q(zarr__size__gt=0)).exists()
            else 0,
            'numberOfFiles': 1 if version.assets.exists() else 0,
        }
        return metadata_for_validation

    def _get_version_validation_result(
        version: Version,
    ) -> tuple[Version.Status, list[dict[str, str]]]:
        try:
            validate(
                _build_validatable_version_metadata(version),
                schema_key='PublishedDandiset',
                json_validation=True,
            )
        except dandischema.exceptions.ValidationError as e:
            logger.info('Error while validating version %s', version.id)
            return (Version.Status.INVALID, _collect_validation_errors(e))
        except ValueError as e:
            # A bare ValueError is thrown when dandischema generates its own exceptions, like a
            # mismatched schemaVersion.
            logger.info('Error while validating version %s', version.id)
            return (Version.Status.INVALID, [{'field': '', 'message': str(e)}])

        logger.info('Successfully validated version %s', version.id)
        return (Version.Status.VALID, [])

    version_id = version.id
    logger.info('Validating dandiset metadata for version %s', version_id)

    # Published versions are immutable
    if version.version != 'draft':
        raise VersionHasBeenPublishedError

    with transaction.atomic():
        # validating version metadata needs to lock the version to avoid racing with
        # other modifications e.g. aggregate_assets_summary.
        version_qs = Version.objects.filter(id=version_id).select_for_update()
        current_version = version_qs.first()

        # It's possible for this version to get deleted during execution of this function.
        # If that happens *before* the select_for_update query, return early.
        if current_version is None:
            logger.info('Version %s no longer exists, skipping validation', version_id)
            return

        # If the version has since been modified, return early
        if current_version.status != Version.Status.PENDING:
            logger.info(
                'Skipping validation for version with a status of %s', current_version.status
            )
            return

        # Set to validating and continue
        version_qs.update(status=Version.Status.VALIDATING)
        status, errors = _get_version_validation_result(current_version)
        version_qs.update(status=status, validation_errors=errors, modified=timezone.now())
