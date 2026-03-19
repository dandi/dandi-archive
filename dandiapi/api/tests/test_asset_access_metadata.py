from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from dandischema.consts import DANDI_SCHEMA_VERSION
from dandischema.models import AccessType
import pytest

from dandiapi.api.models.asset import EmbargoedAssetWithinOpenDandisetError
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.tests.factories import (
    DraftVersionFactory,
)

if TYPE_CHECKING:
    from dandiapi.api.models import Asset


@pytest.mark.django_db
def test_asset_full_metadata_access(
    draft_asset_factory, asset_blob_factory, zarr_archive_factory, embargoed_zarr_archive_factory
):
    raw_metadata = {
        'foo': 'bar',
        'schemaVersion': DANDI_SCHEMA_VERSION,
    }

    # Embargoed
    embargoed_zarr_asset: Asset = draft_asset_factory(
        metadata=raw_metadata, blob=None, zarr=embargoed_zarr_archive_factory()
    )
    embargoed_blob_asset: Asset = draft_asset_factory(
        metadata=raw_metadata, blob=asset_blob_factory(embargoed=True), zarr=None
    )
    embargoed_draft_version = DraftVersionFactory.create(
        dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED
    )
    embargoed_draft_version.assets.add(embargoed_zarr_asset, embargoed_blob_asset)

    # Open
    open_zarr_asset: Asset = draft_asset_factory(
        metadata=raw_metadata, blob=None, zarr=zarr_archive_factory()
    )
    open_blob_asset: Asset = draft_asset_factory(
        metadata=raw_metadata, blob=asset_blob_factory(embargoed=False), zarr=None
    )
    open_draft_version = DraftVersionFactory.create()
    open_draft_version.assets.add(open_zarr_asset, open_blob_asset)

    # Test that access is correctly inferred from embargo status
    for embargoed_asset in [embargoed_zarr_asset, embargoed_blob_asset]:
        assert embargoed_asset.full_metadata['access'][0]['schemaKey'] == 'AccessRequirements'
        assert (
            embargoed_asset.full_metadata['access'][0]['status'] == AccessType.EmbargoedAccess.value
        )

    for open_asset in [open_zarr_asset, open_blob_asset]:
        assert open_asset.full_metadata['access'][0]['schemaKey'] == 'AccessRequirements'
        assert open_asset.full_metadata['access'][0]['status'] == AccessType.OpenAccess.value


@pytest.mark.django_db
def test_access_metadata_open_blob_asset(asset_blob_factory, draft_asset_factory):
    """Open blob asset returns no embargoedUntil."""
    asset = draft_asset_factory(blob=asset_blob_factory(embargoed=False))
    assert asset.access_metadata() == {
        'schemaKey': 'AccessRequirements',
        'status': AccessType.OpenAccess.value,
    }


@pytest.mark.django_db
def test_access_metadata_open_zarr_asset(zarr_archive_factory, draft_asset_factory):
    """Open zarr asset returns no embargoedUntil."""
    zarr = zarr_archive_factory(dandiset__embargo_status=Dandiset.EmbargoStatus.OPEN)
    asset = draft_asset_factory(zarr=zarr, blob=None)
    assert asset.access_metadata() == {
        'schemaKey': 'AccessRequirements',
        'status': AccessType.OpenAccess.value,
    }


@pytest.mark.django_db
def test_access_metadata_embargoed_zarr_with_embargoed_until(
    embargoed_zarr_archive_factory, draft_asset_factory
):
    """Embargoed zarr asset returns embargoedUntil from draft version."""
    zarr = embargoed_zarr_archive_factory(
        dandiset__embargo_end_date=date.fromisoformat('2026-06-15')
    )
    draft_version = zarr.dandiset.draft_version

    asset = draft_asset_factory(zarr=zarr, blob=None)
    draft_version.assets.add(asset)

    assert asset.access_metadata() == {
        'schemaKey': 'AccessRequirements',
        'status': AccessType.EmbargoedAccess.value,
        'embargoedUntil': '2026-06-15',
    }


@pytest.mark.django_db
def test_access_metadata_embargoed_blob_with_embargoed_until(
    embargoed_asset_blob, draft_asset_factory
):
    """Embargoed blob asset returns embargoedUntil from version."""
    draft_version = DraftVersionFactory.create(
        dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED,
        dandiset__embargo_end_date=date.fromisoformat('2026-06-15'),
    )

    asset = draft_asset_factory(blob=embargoed_asset_blob)
    draft_version.assets.add(asset)

    assert asset.access_metadata() == {
        'schemaKey': 'AccessRequirements',
        'status': AccessType.EmbargoedAccess.value,
        'embargoedUntil': '2026-06-15',
    }


@pytest.mark.django_db
def test_access_metadata_embargoed_blob_shared_across_embargoed_dandisets(
    embargoed_asset_blob, draft_asset_factory
):
    """Blob shared by multiple embargoed dandisets returns minimum embargo end date."""
    version_a = DraftVersionFactory.create(
        dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED,
        dandiset__embargo_end_date=date.fromisoformat('2026-08-01'),
    )
    asset_a = draft_asset_factory(blob=embargoed_asset_blob)
    version_a.assets.add(asset_a)

    version_b = DraftVersionFactory.create(
        dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED,
        dandiset__embargo_end_date=date.fromisoformat('2018-10-25'),
    )
    asset_b = draft_asset_factory(blob=embargoed_asset_blob)
    version_b.assets.add(asset_b)

    # Both assets should report the minimum embargo end date
    assert asset_a.access_metadata()['embargoedUntil'] == '2018-10-25'
    assert asset_b.access_metadata()['embargoedUntil'] == '2018-10-25'


@pytest.mark.django_db
def test_access_metadata_embargoed_blob_in_open_dandiset_raises(
    embargoed_asset_blob, draft_asset_factory
):
    """Embargoed blob in an open dandiset raises EmbargoedAssetWithinOpenDandisetError."""
    draft_version = DraftVersionFactory.create(dandiset__embargo_status=Dandiset.EmbargoStatus.OPEN)
    asset = draft_asset_factory(blob=embargoed_asset_blob, zarr=None)
    draft_version.assets.add(asset)

    with pytest.raises(EmbargoedAssetWithinOpenDandisetError):
        asset.access_metadata()
