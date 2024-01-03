from __future__ import annotations
from datetime import timedelta

from django.utils import timezone
import pytest

from dandiapi.api.garbage import stale_assets
from dandiapi.api.models import Asset, Version


@pytest.mark.django_db()
def test_stale_assets(version: Version, draft_asset_factory, published_asset_factory):
    stale_date = timezone.now() - timedelta(days=8)

    for is_stale in (False, True):
        for is_orphaned in (False, True):
            for is_draft in (False, True):
                asset = draft_asset_factory() if is_draft else published_asset_factory()
                if is_stale:
                    asset.modified = stale_date
                    asset.update_modified = False
                    asset.save()
                if not is_orphaned:
                    version.assets.add(asset)
    # The last asset should be stale, orphaned, and draft.
    asset_to_delete = asset

    # Only the last asset should be returned by stale_assets()
    assert stale_assets().get() == asset_to_delete

    # This is how assets will generally be deleted
    stale_assets().delete()

    # The stale asset should be gone
    assert stale_assets().count() == 0
    assert not Asset.objects.filter(id=asset_to_delete.id).exists()

    # The 7 other assets should still be present
    assert Asset.objects.count() == 7
