from __future__ import annotations

from django.db import connection
import pytest

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.search.models import AssetSearch


@pytest.mark.django_db()
def test_assetsearch_visible_to_permissions(draft_asset_factory, draft_version, user_factory):
    asset = draft_asset_factory()
    draft_version.dandiset.embargo_status = Dandiset.EmbargoStatus.EMBARGOED
    draft_version.dandiset.save()
    draft_version.assets.add(asset)

    with connection.cursor() as cursor:
        cursor.execute('REFRESH MATERIALIZED VIEW asset_search;')

    assert AssetSearch.objects.count() == 1
    other_user = user_factory()
    assert AssetSearch.objects.visible_to(other_user).count() == 0
