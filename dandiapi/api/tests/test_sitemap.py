from __future__ import annotations

from dandischema.consts import DANDI_SCHEMA_VERSION
from django.conf import settings
from django.urls import reverse
import pytest

from dandiapi.api.models import Dandiset
from dandiapi.api.services.asset import add_asset_to_version
from dandiapi.api.tests.factories import AssetBlobFactory, DraftVersionFactory, UserFactory


@pytest.mark.django_db
def test_sitemap(api_client):
    user = UserFactory.create()
    nonempty = DraftVersionFactory.create(dandiset__owners=[user])
    empty = DraftVersionFactory.create(dandiset__owners=[user])
    embargoed = DraftVersionFactory.create(
        dandiset__owners=[user], dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED
    )
    for version in [nonempty, embargoed]:
        add_asset_to_version(
            user=user,
            version=version,
            asset_blob=AssetBlobFactory.create(),
            metadata={'path': 'foo/bar.txt', 'schemaVersion': DANDI_SCHEMA_VERSION},
        )

    response = api_client.get(reverse('sitemap'))
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/xml'

    content = response.content.decode()
    assert (
        f'<loc>{settings.DANDI_WEB_APP_URL}/dandiset/{nonempty.dandiset.identifier}</loc>'
        in content
    )
    assert f'/dandiset/{empty.dandiset.identifier}</loc>' not in content
    assert f'/dandiset/{embargoed.dandiset.identifier}</loc>' not in content
