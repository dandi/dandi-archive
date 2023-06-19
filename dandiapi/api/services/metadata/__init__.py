from celery.utils.log import get_task_logger
import dandischema.exceptions
from dandischema.metadata import aggregate_assets_summary, validate
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import jsonschema.exceptions

from dandiapi.api.models import Asset, Version
from dandiapi.api.services.metadata.exceptions import AssetHasBeenPublished, VersionHasBeenPublished
from dandiapi.api.services.publish import _build_publishable_version_from_draft

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


def validate_asset_metadata(*, asset: Asset) -> None:
    logger.info('Validating asset metadata for asset %s', asset.id)

    # Published assets are immutable
    if asset.published:
        raise AssetHasBeenPublished()

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

        # Save asset
        asset.save()

        # Update modified timestamps on all draft versions this asset belongs to
        asset.versions.filter(version='draft').update(modified=timezone.now())


def version_aggregate_assets_summary(version: Version) -> None:
    if version.version != 'draft':
        raise VersionHasBeenPublished()

    version.metadata['assetsSummary'] = aggregate_assets_summary(
        version.assets.filter(status=Asset.Status.VALID)
        .values_list('metadata', flat=True)
        .iterator()
    )

    Version.objects.filter(id=version.id, version='draft').update(
        modified=timezone.now(), metadata=version.metadata
    )


def validate_version_metadata(*, version: Version) -> None:
    def _build_validatable_version_metadata(version: Version) -> dict:
        # since Version.Status.VALID is a proxy for a version being publishable, we need to
        # validate against the PublishedDandiset schema even though we lack several things
        # at validation time: id, url, doi, and assetsSummary. this tricks the validator into
        # giving us the useful errors we need but ignoring the other errors we can't satisfy yet.
        publishable_version = _build_publishable_version_from_draft(version)
        metadata_for_validation = publishable_version.metadata

        metadata_for_validation[
            'id'
        ] = f'DANDI:{publishable_version.dandiset.identifier}/{publishable_version.version}'  # noqa
        metadata_for_validation[
            'url'
        ] = f'{settings.DANDI_WEB_APP_URL}/dandiset/{publishable_version.dandiset.identifier}/{publishable_version.version}'  # noqa
        metadata_for_validation['doi'] = '10.80507/dandi.123456/0.123456.1234'
        metadata_for_validation['assetsSummary'] = {
            'schemaKey': 'AssetsSummary',
            'numberOfBytes': 1 if version.assets.filter(blob__size__gt=0).exists() else 0,
            'numberOfFiles': 1 if version.assets.exists() else 0,
        }
        return metadata_for_validation

    logger.info('Validating dandiset metadata for version %s', version.id)

    # Published versions are immutable
    if version.version != 'draft':
        raise VersionHasBeenPublished()

    with transaction.atomic():
        # validating version metadata needs to lock the version to avoid racing with
        # other modifications e.g. aggregate_assets_summary.
        version = (
            Version.objects.filter(id=version.id, status=Version.Status.PENDING)
            .select_for_update()
            .first()
        )
        version.status = Version.Status.VALIDATING
        version.save()

        try:
            validate(
                _build_validatable_version_metadata(version),
                schema_key='PublishedDandiset',
                json_validation=True,
            )
        except dandischema.exceptions.ValidationError as e:
            logger.info('Error while validating version %s', version.id)
            version.status = Version.Status.INVALID

            validation_errors = _collect_validation_errors(e)
            version.validation_errors = validation_errors
            version.save()
            return
        except ValueError as e:
            # A bare ValueError is thrown when dandischema generates its own exceptions, like a
            # mismatched schemaVersion.
            version.status = Version.Status.INVALID
            version.validation_errors = [{'field': '', 'message': str(e)}]
            version.save()
            return
        logger.info('Successfully validated version %s', version.id)
        version.status = Version.Status.VALID
        version.validation_errors = []
        version.save()
