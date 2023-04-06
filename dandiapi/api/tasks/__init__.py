from celery import shared_task
from celery.utils.log import get_task_logger
import dandischema.exceptions
from dandischema.metadata import validate
from django.db import transaction
from django.db.models import QuerySet
from django.db.transaction import atomic
import jsonschema.exceptions

from dandiapi.api import doi
from dandiapi.api.asset_paths import add_version_asset_paths
from dandiapi.api.doi import delete_doi
from dandiapi.api.manifests import (
    write_assets_jsonld,
    write_assets_yaml,
    write_collection_jsonld,
    write_dandiset_jsonld,
    write_dandiset_yaml,
)
from dandiapi.api.models import Asset, AssetBlob, Dandiset, EmbargoedAssetBlob, Version

logger = get_task_logger(__name__)


@shared_task(queue='calculate_sha256', soft_time_limit=86_400)
@atomic
def calculate_sha256(blob_id: int) -> None:
    try:
        asset_blob = AssetBlob.objects.get(blob_id=blob_id)
        logger.info(f'Found AssetBlob {blob_id}')
    except AssetBlob.DoesNotExist:
        asset_blob = EmbargoedAssetBlob.objects.get(blob_id=blob_id)
        logger.info(f'Found EmbargoedAssetBlob {blob_id}')

    sha256 = asset_blob.blob.storage.sha256_checksum(asset_blob.blob.name)

    # TODO: Run dandi-cli validation

    asset_blob.sha256 = sha256
    asset_blob.save()

    # The newly calculated sha256 digest will be included in the metadata, so we need to revalidate
    # Note, we use `.iterator` here and delay each validation as a new task in order to keep memory
    # usage down.
    def dispatch_validation():
        for asset_id in asset_blob.assets.values_list('id', flat=True).iterator():
            # Note: while asset metadata is fairly lightweight compute-wise, memory-wise it can
            # become an issue during serialization/deserialization of the JSON blob by pydantic.
            # Therefore, we delay each validation to its own task.
            validate_asset_metadata.delay(asset_id)

    # Run on transaction commit
    transaction.on_commit(dispatch_validation)


@shared_task(soft_time_limit=60)
@atomic
def write_manifest_files(version_id: int) -> None:
    version: Version = Version.objects.get(id=version_id)
    _log_version_action('Writing manifests for', version_id, version)

    write_dandiset_yaml(version)
    write_assets_yaml(version)
    write_dandiset_jsonld(version)
    write_assets_jsonld(version)
    write_collection_jsonld(version)


def encode_pydantic_error(error) -> dict[str, str]:
    return {'field': error['loc'][0], 'message': error['msg']}


def encode_jsonschema_error(error: jsonschema.exceptions.ValidationError) -> dict[str, str]:
    return {'field': '.'.join([str(p) for p in error.path]), 'message': error.message}


def collect_validation_errors(
    error: dandischema.exceptions.ValidationError,
) -> list[dict[str, str]]:
    if type(error) is dandischema.exceptions.PydanticValidationError:
        encoder = encode_pydantic_error
    elif type(error) is dandischema.exceptions.JsonschemaValidationError:
        encoder = encode_jsonschema_error
    else:
        raise error
    return [encoder(error) for error in error.errors]


@shared_task(soft_time_limit=10)
@atomic
# This method takes both a version_id and an asset_id because asset metadata renders differently
# depending on which version the asset belongs to.
def validate_asset_metadata(asset_id: int) -> None:
    logger.info('Validating asset metadata for asset %s', asset_id)
    asset: Asset = Asset.objects.get(id=asset_id)

    asset.status = Asset.Status.VALIDATING
    asset.save()

    try:
        metadata = asset.published_metadata()
        validate(metadata, schema_key='PublishedAsset', json_validation=True)
    except dandischema.exceptions.ValidationError as e:
        logger.info('Error while validating asset %s', asset_id)
        asset.status = Asset.Status.INVALID

        validation_errors = collect_validation_errors(e)
        asset.validation_errors = validation_errors
        asset.save()
        return
    except ValueError as e:
        # A bare ValueError is thrown when dandischema generates its own exceptions, like a
        # mismatched schemaVersion.
        asset.status = Asset.Status.INVALID
        asset.validation_errors = [{'field': '', 'message': str(e)}]
        asset.save()
        return
    logger.info('Successfully validated asset %s', asset_id)
    asset.status = Asset.Status.VALID
    asset.validation_errors = []
    asset.save()


@shared_task(soft_time_limit=30)
@atomic
def validate_version_metadata(version_id: int) -> None:
    version: Version = Version.objects.get(id=version_id)
    _log_version_action('Validating dandiset metadata', version_id, version)

    version.status = Version.Status.VALIDATING
    version.save()

    try:
        publish_version = version.publish_version
        metadata = publish_version.metadata

        # Inject a dummy DOI so the metadata is valid
        metadata['doi'] = '10.80507/dandi.123456/0.123456.1234'

        validate(metadata, schema_key='PublishedDandiset', json_validation=True)
    except dandischema.exceptions.ValidationError as e:
        _log_version_action('Error while validating dandiset metadata', version_id, version)
        version.status = Version.Status.INVALID

        validation_errors = collect_validation_errors(e)
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
    _log_version_action('Successfully validated dandiset metadata', version_id, version)
    version.status = Version.Status.VALID
    version.validation_errors = []
    version.save()


@shared_task
def delete_doi_task(doi: str) -> None:
    delete_doi(doi)


@shared_task
def unembargo_dandiset(dandiset_id: int):
    """Unembargo a dandiset by copying all embargoed asset blobs to the public bucket."""
    dandiset: Dandiset = Dandiset.objects.get(id=dandiset_id)

    # Only the draft version is needed, since embargoed dandisets can't be published
    draft_version: Version = dandiset.draft_version
    embargoed_assets: QuerySet[Asset] = draft_version.assets.filter(embargoed_blob__isnull=False)

    # Unembargo all assets
    for asset in embargoed_assets.iterator():
        asset.unembargo()

    # Update draft version metadata
    draft_version.metadata['access'] = [
        {'schemaKey': 'AccessRequirements', 'status': 'dandi:OpenAccess'}
    ]
    draft_version.save(update_fields=['metadata'])

    # Set access on dandiset
    dandiset.embargo_status = Dandiset.EmbargoStatus.OPEN
    dandiset.save(update_fields=['embargo_status'])


@shared_task
@atomic
def publish_task(version_id: int):
    old_version: Version = Version.objects.get(id=version_id)
    new_version: Version = old_version.publish_version
    new_version.save()

    # Bulk create the join table rows to optimize linking assets to new_version
    AssetVersions = Version.assets.through

    # Add a new many-to-many association directly to any already published assets
    already_published_assets = old_version.assets.filter(published=True)
    AssetVersions.objects.bulk_create(
        [
            AssetVersions(asset_id=asset['id'], version_id=new_version.id)
            for asset in already_published_assets.values('id')
        ]
    )

    # Publish any draft assets
    draft_assets = old_version.assets.filter(published=False).all()
    for draft_asset in draft_assets:
        draft_asset.publish()
    Asset.objects.bulk_update(draft_assets, ['metadata', 'published'])

    AssetVersions.objects.bulk_create(
        [AssetVersions(asset_id=asset.id, version_id=new_version.id) for asset in draft_assets]
    )

    # Save again to recompute metadata, specifically assetsSummary
    new_version.save()

    # Add asset paths with new version
    add_version_asset_paths(version=new_version)

    # Set the version of the draft to PUBLISHED so that it cannot be published again without
    # being modified and revalidated
    old_version.status = Version.Status.PUBLISHED
    old_version.save()

    # Write updated manifest files and create DOI after published version has been committed to DB.
    transaction.on_commit(lambda: write_manifest_files.delay(new_version.id))

    def _create_doi(version_id: int):
        version = Version.objects.get(id=version_id)
        version.doi = doi.create_doi(version)
        version.save()

    transaction.on_commit(lambda: _create_doi(new_version.id))


def _log_version_action(msg: str, version: Version) -> None:
    """Centralize/harmonize logging of operations over a Version."""

    logger.info(f'{msg} for version {version.id}, {version}')
