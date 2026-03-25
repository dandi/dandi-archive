from __future__ import annotations

from django.db import connection
import pytest

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.tests.factories import DraftVersionFactory, UserFactory
from dandiapi.search.models import AssetSearch


@pytest.mark.django_db
def test_assetsearch_visible_to_permissions(draft_asset_factory):
    asset = draft_asset_factory()
    draft_version = DraftVersionFactory.create(
        dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED
    )
    draft_version.assets.add(asset)

    with connection.cursor() as cursor:
        cursor.execute('REFRESH MATERIALIZED VIEW asset_search;')

    assert AssetSearch.objects.count() == 1
    other_user = UserFactory.create()
    assert AssetSearch.objects.visible_to(other_user).count() == 0
