from datetime import timedelta

from django.utils import timezone
import pytest

from dandiapi.api.garbage import stale_assets
from dandiapi.api.models import Asset, Version


@pytest.mark.django_db
def test_stale_assets(version: Version, asset_factory):

    stale_orphan_asset: Asset = asset_factory()
    stale_linked_asset: Asset = asset_factory()
    fresh_orphan_asset: Asset = asset_factory()  # noqa: F841
    fresh_linked_asset: Asset = asset_factory()

    # link the linked assets
    version.assets.add(stale_linked_asset)
    version.assets.add(fresh_linked_asset)

    # Spoof the modified dates on the stale assets
    stale_date = timezone.now() - timedelta(days=8)
    stale_orphan_asset.modified = stale_date
    stale_orphan_asset.update_modified = False
    stale_orphan_asset.save()
    stale_linked_asset.modified = stale_date
    stale_linked_asset.update_modified = False
    stale_linked_asset.save()

    # Only the stale orphan asset should be returned by stale_assets()
    assert stale_assets().get() == stale_orphan_asset

    # This is how assets will generally be deleted
    stale_assets().delete()

    # The stale asset should be gone
    assert stale_assets().count() == 0
    # The three other assets should still be present
    assert Asset.objects.count() == 3
