from __future__ import annotations

import copy
import datetime
import logging
from typing import TYPE_CHECKING

from dandischema.metadata import aggregate_assets_summary, validate
from django.contrib.auth.models import User
from django.db import transaction
from more_itertools import ichunked
import requests

from dandiapi.api import doi
from dandiapi.api.asset_paths import add_version_asset_paths
from dandiapi.api.models import Asset, Dandiset, Version
from dandiapi.api.services import audit
from dandiapi.api.services.exceptions import NotAllowedError
from dandiapi.api.services.permissions.dandiset import is_dandiset_owner
from dandiapi.api.services.publish.exceptions import (
    DandisetAlreadyPublishedError,
    DandisetAlreadyPublishingError,
    DandisetBeingValidatedError,
    DandisetInvalidMetadataError,
    DandisetNotLockedError,
    DandisetValidationPendingError,
)
from dandiapi.api.tasks import promote_version_doi_task, write_manifest_files

if TYPE_CHECKING:
    from django.db.models import QuerySet

logger = logging.getLogger(__name__)


def publish_asset(*, asset: Asset) -> None:
    with transaction.atomic():
        # Lock asset to ensure it doesn't change out from under us while publishing
        locked_asset = Asset.objects.select_for_update().get(id=asset.id)

        if locked_asset.published:
            raise RuntimeError('Asset is already published')
        if locked_asset.status != Asset.Status.VALID:
            raise RuntimeError('Asset does not have VALID status')

        # Publish the asset
        locked_asset.metadata = asset.published_metadata()
        locked_asset.published = True
        locked_asset.save()


def _lock_dandiset_for_publishing(*, user: User, dandiset: Dandiset) -> None:  # noqa: C901
    """
    Prepare a dandiset to be published by locking it and setting its status to PUBLISHING.

    This function MUST be called before _publish_dandiset is called.
    """
    if not is_dandiset_owner(dandiset, user):
        raise NotAllowedError

    if dandiset.embargo_status != Dandiset.EmbargoStatus.OPEN:
        raise NotAllowedError('Operation only allowed on OPEN dandisets', 400)

    with transaction.atomic():
        draft_version: Version = dandiset.versions.select_for_update().get(version='draft')

        if draft_version.assets.filter(zarr__isnull=False).exists():
            raise NotAllowedError('Cannot publish dandisets which contain zarrs', 400)

        if not draft_version.publishable:
            match draft_version.status:
                case Version.Status.PUBLISHED:
                    raise DandisetAlreadyPublishedError
                case Version.Status.PUBLISHING:
                    raise DandisetAlreadyPublishingError
                case Version.Status.VALIDATING:
                    raise DandisetBeingValidatedError
                case Version.Status.INVALID:
                    raise DandisetInvalidMetadataError
                case Version.Status.PENDING:
                    raise DandisetValidationPendingError
                case Version.Status.VALID:
                    raise DandisetInvalidMetadataError
                case other:
                    raise NotImplementedError(
                        f'Draft version of dandiset {dandiset.identifier} '
                        f'has unknown status "{other}".'
                    )

        draft_version.status = Version.Status.PUBLISHING
        draft_version.save()


def _build_publishable_version_from_draft(
    draft_version: Version, *, version: str | None = None, doi: str | None = None
) -> Version:
    # Make a deep copy of the dict to avoid mutating the draft version's metadata.
    publishable_version_metadata = copy.deepcopy(draft_version.metadata)

    now = datetime.datetime.now(datetime.UTC)
    # inject the publishedBy and datePublished fields
    publishable_version_metadata.update(
        {
            'publishedBy': draft_version.published_by(now),
            'datePublished': now.isoformat(),
        }
    )

    release_notes = draft_version.release_notes
    if release_notes:
        publishable_version_metadata['releaseNotes'] = release_notes

    return Version(
        dandiset=draft_version.dandiset,
        name=draft_version.name,
        metadata=publishable_version_metadata,
        release_notes=draft_version.release_notes,
        status=Version.Status.VALID,
        version=version or Version.next_published_version(draft_version.dandiset),
        doi=doi,
    )


def _release_draft_lock(dandiset_id: int) -> None:
    Version.objects.filter(
        dandiset_id=dandiset_id, version='draft', status=Version.Status.PUBLISHING
    ).update(status=Version.Status.VALID)


def _publish_dandiset(dandiset_id: int, user_id: int) -> None:
    """
    Publish a dandiset.

    Calling `_lock_dandiset_for_publishing()` is a precondition for calling this function.
    """
    draft_version: Version = Version.objects.get(dandiset_id=dandiset_id, version='draft')
    if draft_version.status != Version.Status.PUBLISHING:
        raise DandisetNotLockedError(
            'Dandiset must be in PUBLISHING state. Call `_lock_dandiset_for_publishing()` '
            'before this function.'
        )

    # The draft is locked in PUBLISHING, so no other publish of this dandiset can run and the
    # version string chosen here stays free until the transaction below commits it.
    version_str = Version.next_published_version(draft_version.dandiset)
    new_doi = doi.format_doi(draft_version.dandiset.identifier, version_str)

    # Reserve the DOI as a Draft before anything irreversible happens. If DataCite cannot be
    # reached, the publish is aborted with nothing to clean up.
    reserved = doi.doi_configured()
    if reserved:
        try:
            doi.reserve_doi(new_doi)
        except requests.RequestException:
            _release_draft_lock(dandiset_id)
            raise

    try:
        _commit_published_version(
            dandiset_id, user_id, version=version_str, doi=new_doi, promote=reserved
        )
    except Exception:
        # A Draft DOI is invisible and deletable, so a stray one from a failed publish is
        # harmless even if this cleanup fails too.
        if reserved:
            try:
                doi.delete_doi(new_doi)
            except requests.RequestException:
                logger.exception('Failed to clean up reserved DOI %s', new_doi)
        _release_draft_lock(dandiset_id)
        raise


def _commit_published_version(
    dandiset_id: int, user_id: int, *, version: str, doi: str, promote: bool
) -> None:
    with transaction.atomic():
        old_version: Version = Version.objects.select_for_update().get(
            dandiset_id=dandiset_id,
            version='draft',
        )

        new_version: Version = _build_publishable_version_from_draft(
            old_version, version=version, doi=doi
        )
        new_version.save()

        # Bulk create the join table rows to optimize linking assets to new_version
        AssetVersions = Version.assets.through  # noqa: N806

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

        # Copy the finalized assetsSummary to the draft version in case it wasn't up to date
        # before starting the publish.
        old_version.metadata['assetsSummary'] = new_version.metadata['assetsSummary']
        # Set the version of the draft to PUBLISHED so that it cannot be published again without
        # being modified and revalidated
        old_version.status = Version.Status.PUBLISHED
        old_version.save()

        validate(new_version.metadata, schema_key='PublishedDandiset', json_validation=True)

        # The DOI is already in the version's metadata, so the manifests do not need to wait on
        # DataCite; promotion to Findable happens independently.
        write_manifest_files.delay_on_commit(new_version.id)
        if promote:
            promote_version_doi_task.delay_on_commit(new_version.id)

        user = User.objects.get(id=user_id)
        audit.publish_dandiset(
            dandiset=new_version.dandiset, user=user, version=new_version.version
        )


def publish_dandiset(*, user: User, dandiset: Dandiset, release_notes: str | None = None) -> None:
    from dandiapi.api.tasks import publish_dandiset_task

    with transaction.atomic():
        _lock_dandiset_for_publishing(user=user, dandiset=dandiset)

        Version.objects.filter(dandiset=dandiset, version='draft').update(
            release_notes=release_notes or ''
        )

        transaction.on_commit(lambda: publish_dandiset_task.delay(dandiset.id, user.id))
