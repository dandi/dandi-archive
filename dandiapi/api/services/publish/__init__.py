import datetime

from dandischema.metadata import aggregate_assets_summary, validate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import QuerySet
from more_itertools import ichunked

from dandiapi.api import doi
from dandiapi.api.asset_paths import add_version_asset_paths
from dandiapi.api.models import Asset, Dandiset, Version
from dandiapi.api.services.exceptions import NotAllowed
from dandiapi.api.services.publish.exceptions import (
    DandisetAlreadyPublished,
    DandisetAlreadyPublishing,
    DandisetBeingValidated,
    DandisetInvalidMetadata,
    DandisetNotLocked,
    DandisetValidationPending,
)
from dandiapi.api.tasks import write_manifest_files


def publish_asset(*, asset: Asset) -> None:
    with transaction.atomic():
        # Lock asset to ensure it doesn't change out from under us while publishing
        locked_asset = Asset.objects.select_for_update().get(id=asset.id)

        assert not locked_asset.published, 'asset is already published'
        assert locked_asset.status == Asset.Status.VALID, 'asset is not VALID'

        # Publish the asset
        locked_asset.metadata = asset.published_metadata()
        locked_asset.published = True
        locked_asset.save()


def _lock_dandiset_for_publishing(*, user: User, dandiset: Dandiset) -> None:
    """
    Prepare a dandiset to be published by locking it and setting its status to PUBLISHING.

    This function MUST be called before _publish_dandiset is called.
    """
    if (
        not user.has_perm('owner', dandiset)
        or dandiset.embargo_status != Dandiset.EmbargoStatus.OPEN
    ):
        raise NotAllowed()
    if dandiset.zarr_archives.exists() or dandiset.embargoed_zarr_archives.exists():
        # TODO: return a string instead of a list here
        raise NotAllowed(['Cannot publish dandisets which contain zarrs'], 400)  # type: ignore

    with transaction.atomic():
        draft_version: Version = dandiset.versions.select_for_update().get(version='draft')
        if not draft_version.publishable:
            match draft_version.status:
                case Version.Status.PUBLISHED:
                    raise DandisetAlreadyPublished()
                case Version.Status.PUBLISHING:
                    raise DandisetAlreadyPublishing()
                case Version.Status.VALIDATING:
                    raise DandisetBeingValidated()
                case Version.Status.INVALID:
                    raise DandisetInvalidMetadata()
                case Version.Status.PENDING:
                    raise DandisetValidationPending()
                case Version.Status.VALID:
                    raise DandisetInvalidMetadata()
                case other:
                    raise NotImplementedError(
                        f'Draft version of dandiset {dandiset.identifier} '
                        f'has unknown status "{other}".'
                    )

        draft_version.status = Version.Status.PUBLISHING
        draft_version.save()


def _build_publishable_version_from_draft(draft_version: Version) -> Version:
    publishable_version = Version(
        dandiset=draft_version.dandiset,
        name=draft_version.name,
        metadata=draft_version.metadata,
        status=Version.Status.VALID,
        version=Version.next_published_version(draft_version.dandiset),
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    # inject the publishedBy and datePublished fields
    publishable_version.metadata.update(
        {
            'publishedBy': draft_version.published_by(now),
            'datePublished': now.isoformat(),
        }
    )

    return publishable_version


def _publish_dandiset(dandiset_id: int) -> None:
    """
    Publish a dandiset.

    Calling `_lock_dandiset_for_publishing()` is a precondition for calling this function.
    """
    with transaction.atomic():
        old_version: Version = Version.objects.select_for_update().get(
            dandiset_id=dandiset_id,
            version='draft',
        )

        if old_version.status != Version.Status.PUBLISHING:
            raise DandisetNotLocked(
                'Dandiset must be in PUBLISHING state. Call `_lock_dandiset_for_publishing()` '
                'before this function.'
            )

        new_version: Version = _build_publishable_version_from_draft(old_version)
        new_version.save()

        # Bulk create the join table rows to optimize linking assets to new_version
        AssetVersions = Version.assets.through

        # Add a new many-to-many association directly to any already published assets
        already_published_assets: QuerySet[Asset] = old_version.assets.filter(published=True)

        # Batch bulk creates to avoid blowing up memory when there are a lot of assets
        for asset_ids_batch in ichunked(
            already_published_assets.values_list('id', flat=True).iterator(), 5_000
        ):
            AssetVersions.objects.bulk_create(
                [
                    AssetVersions(asset_id=asset_id, version_id=new_version.id)
                    for asset_id in asset_ids_batch
                ]
            )

        draft_assets: QuerySet[Asset] = old_version.assets.filter(published=False)

        # Batch bulk creates to avoid blowing up memory when there are a lot of assets
        for asset_ids_batch in ichunked(
            draft_assets.values_list('id', flat=True).iterator(), 5_000
        ):
            AssetVersions.objects.bulk_create(
                [
                    AssetVersions(asset_id=asset_id, version_id=new_version.id)
                    for asset_id in asset_ids_batch
                ]
            )

        # Publish any draft assets
        for draft_asset in draft_assets.iterator():
            publish_asset(asset=draft_asset)

        # Since all assets in new_version are published, their metadata is already compliant,
        # and there is no need to use `.full_metadata`
        new_version.metadata['assetsSummary'] = aggregate_assets_summary(
            new_version.assets.values_list('metadata', flat=True).iterator()
        )
        new_version.save()

        # Add asset paths with new version
        add_version_asset_paths(version=new_version)

        # Set the version of the draft to PUBLISHED so that it cannot be published again without
        # being modified and revalidated
        old_version.status = Version.Status.PUBLISHED
        old_version.save()

        # Inject a dummy DOI so the metadata is valid
        new_version.metadata['doi'] = '10.80507/dandi.123456/0.123456.1234'

        validate(new_version.metadata, schema_key='PublishedDandiset', json_validation=True)

        # Write updated manifest files and create DOI after
        # published version has been committed to DB.
        transaction.on_commit(lambda: write_manifest_files.delay(new_version.id))

        def _create_doi(version_id: int):
            version = Version.objects.get(id=version_id)
            version.doi = doi.create_doi(version)
            version.save()

        transaction.on_commit(lambda: _create_doi(new_version.id))


def publish_dandiset(*, user: User, dandiset: Dandiset) -> None:
    from dandiapi.api.tasks import publish_dandiset_task

    with transaction.atomic():
        _lock_dandiset_for_publishing(user=user, dandiset=dandiset)
        transaction.on_commit(lambda: publish_dandiset_task.delay(dandiset.id))
