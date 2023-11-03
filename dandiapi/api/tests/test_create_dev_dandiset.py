from __future__ import annotations

import pytest

from dandiapi.api.management.commands.create_dev_dandiset import create_dev_dandiset
from dandiapi.api.models import Asset, AssetBlob, Dandiset, Version


@pytest.mark.django_db()
def test_create_dev_dandiset(user):
    create_dev_dandiset('--name', 'My Test Dandiset', '--owner', user.email)

    assert Dandiset.objects.count() == 1
    dandiset = Dandiset.objects.get()
    assert user in dandiset.owners

    assert Version.objects.count() == 1
    version = Version.objects.get()
    assert version.dandiset == dandiset
    assert version.version == 'draft'
    assert version.status == Version.Status.VALID

    assert Asset.objects.count() == 1
    asset = Asset.objects.get()
    assert asset in version.assets.all()

    assert AssetBlob.objects.count() == 1
    asset_blob = AssetBlob.objects.get()
    assert AssetBlob.blob.field.storage.exists(asset_blob.blob.name)
