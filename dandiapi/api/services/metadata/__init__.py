from celery.utils.log import get_task_logger
import dandischema.exceptions
from dandischema.metadata import validate
from django.db import transaction
from django.utils import timezone
import jsonschema.exceptions

from dandiapi.api.models import Asset, Version
from dandiapi.api.services.metadata.exceptions import AssetHasBeenPublished, VersionHasBeenPublished

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
        asset.status = Asset.Status.VALIDATING
        asset.save()

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


def validate_version_metadata(*, version: Version) -> None:
    logger.info('Validating dandiset metadata for version %s', version.id)

    # Published versions are immutable
    if version.version != 'draft':
        raise VersionHasBeenPublished()

    with transaction.atomic():
        version.status = Version.Status.VALIDATING
        version.save()

        try:
            publish_version = version.publish_version
            metadata = publish_version.metadata

            # Inject a dummy DOI so the metadata is valid
            metadata['doi'] = '10.80507/dandi.123456/0.123456.1234'

            validate(metadata, schema_key='PublishedDandiset', json_validation=True)
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
