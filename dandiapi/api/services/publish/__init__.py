from django.contrib.auth.models import User
from django.db import transaction

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
        if draft_version.status != Version.Status.VALID:
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
                case other:
                    raise NotImplementedError(
                        f'Draft version of dandiset {dandiset.identifier} '
                        f'has unknown status "{other}".'
                    )

        draft_version.status = Version.Status.PUBLISHING
        draft_version.save()


def _publish_dandiset(dandiset_id: int) -> None:
    """
    Publish a dandiset.

    Calling `_lock_dandiset_for_publishing()` is a precondition for calling this function.
    """
    old_version: Version = (
        Dandiset.objects.get(id=dandiset_id).versions.select_for_update().get(version='draft')
    )

    with transaction.atomic():
        if old_version.status != Version.Status.PUBLISHING:
            raise DandisetNotLocked(
                'Dandiset must be in PUBLISHING state. Call `_lock_dandiset_for_publishing()` '
                'before this function.'
            )

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

    if (
        not user.has_perm('owner', dandiset)
        or dandiset.embargo_status != Dandiset.EmbargoStatus.OPEN
    ):
        raise NotAllowed()
    if dandiset.zarr_archives.exists() or dandiset.embargoed_zarr_archives.exists():
        # TODO: return a string instead of a list here
        raise NotAllowed(['Cannot publish dandisets which contain zarrs'], 400)  # type: ignore

    with transaction.atomic():
        _lock_dandiset_for_publishing(user=user, dandiset=dandiset)
        transaction.on_commit(lambda: publish_dandiset_task.delay(dandiset.id))
