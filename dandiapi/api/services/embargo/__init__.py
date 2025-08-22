from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import transaction

from dandiapi.api.mail import send_dandiset_unembargoed_message
from dandiapi.api.models import AssetBlob, Dandiset, Version
from dandiapi.api.models.asset import Asset
from dandiapi.api.services import audit
from dandiapi.api.services.asset.exceptions import DandisetOwnerRequiredError
from dandiapi.api.services.embargo.utils import remove_dandiset_embargo_tags
from dandiapi.api.services.exceptions import DandiError
from dandiapi.api.services.metadata import validate_version_metadata
from dandiapi.api.services.permissions.dandiset import is_dandiset_owner
from dandiapi.api.tasks import unembargo_dandiset_task

from .exceptions import (
    AssetBlobEmbargoedError,
    DandisetActiveUploadsError,
    DandisetNotEmbargoedError,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import User


logger = logging.getLogger(__name__)


@transaction.atomic()
def unembargo_dandiset(ds: Dandiset, user: User):
    """Unembargo a dandiset by copying all embargoed asset blobs to the public bucket."""
    logger.info('Unembargoing Dandiset %s', ds.identifier)
    logger.info('\t%s assets', ds.draft_version.assets.count())

    if ds.embargo_status != Dandiset.EmbargoStatus.UNEMBARGOING:
        raise DandiError(
            message=f'Expected dandiset state {Dandiset.EmbargoStatus.UNEMBARGOING}, found {ds.embargo_status}',  # noqa: E501
            http_status_code=500,
        )
    if ds.uploads.all().exists():
        raise DandisetActiveUploadsError(http_status_code=500)

    # Remove tags in S3
    logger.info('Removing tags...')
    remove_dandiset_embargo_tags(ds)

    # Set all assets to pending
    updated_assets = Asset.objects.filter(versions__dandiset=ds).update(status=Asset.Status.PENDING)
    # Update embargoed flag on asset blobs
    # Zarrs have no such property as it is derived from the dandiset
    updated_blobs = AssetBlob.objects.filter(embargoed=True, assets__versions__dandiset=ds).update(
        embargoed=False
    )
    logger.info('Set %s assets to PENDING', updated_assets)
    logger.info('Updated %s asset blobs', updated_blobs)

    # Set status to OPEN
    Dandiset.objects.filter(pk=ds.pk).update(embargo_status=Dandiset.EmbargoStatus.OPEN)
    logger.info('Dandiset embargo status updated')

    # Fetch version to ensure changed embargo_status is included
    # Save version to update metadata through populate_metadata
    v = Version.objects.select_for_update().get(dandiset=ds, version='draft')
    v.status = Version.Status.PENDING
    v.save()
    logger.info('Version metadata updated')

    # Pre-emptively validate version metadata, so that old validation
    # errors don't show up once un-embargo is finished
    validate_version_metadata(version=v)
    logger.info('Version metadata validated')

    # Notify owners of completed unembargo
    send_dandiset_unembargoed_message(ds)
    logger.info('Dandiset owners notified.')

    logger.info('...Done')

    audit.unembargo_dandiset(dandiset=ds, user=user)


def remove_asset_blob_embargoed_tag(asset_blob: AssetBlob) -> None:
    """Remove the embargoed tag of an asset blob."""
    if asset_blob.embargoed:
        raise AssetBlobEmbargoedError

    asset_blob.blob.storage.delete_tags(asset_blob.blob.name)


def kickoff_dandiset_unembargo(*, user: User, dandiset: Dandiset):
    """Set dandiset status to kickoff unembargo."""
    if dandiset.embargo_status != Dandiset.EmbargoStatus.EMBARGOED:
        raise DandisetNotEmbargoedError

    if not is_dandiset_owner(dandiset, user):
        raise DandisetOwnerRequiredError

    if dandiset.uploads.count():
        raise DandisetActiveUploadsError

    with transaction.atomic():
        Dandiset.objects.filter(pk=dandiset.pk).update(
            embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING
        )
        transaction.on_commit(lambda: unembargo_dandiset_task.delay(dandiset.pk, user.id))
