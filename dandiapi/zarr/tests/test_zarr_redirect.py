from __future__ import annotations

import pytest
from zarr_checksum.checksum import EMPTY_CHECKSUM

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.services.permissions.dandiset import (
    add_dandiset_owner,
    get_dandiset_owners,
    replace_dandiset_owners,
)
from dandiapi.api.tests.factories import DandisetFactory, UserFactory
from dandiapi.api.tests.fuzzy import UUID_RE
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus
from dandiapi.zarr.tasks import ingest_zarr_archive
from dandiapi.zarr.tests.factories import EmbargoedZarrArchiveFactory, ZarrArchiveFactory

# @pytest.mark.django_db
# def test_zarr_redirect(api_client, embargoed_zarr_archive_factory):
#     user = UserFactory.create()
#     api_client.force_authenticate(user=user)
#     zarr_archive: ZarrArchive = ZarrArchiveFactory.create(dandiset__owners=[user])

#     resp = api_client.get(
#         f'/api/zarr/{zarr_archive.zarr_id}/',
#         {
#             'name': zarr_archive.name,
#             'dandiset': zarr_archive.dandiset.identifier,
#         },
#     )
#     assert resp.status_code == 400
#     assert resp.json() == ['Zarr already exists']


@pytest.mark.django_db
def test_zarr_redirect_(api_client, embargoed_zarr_archive_factory):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive: ZarrArchive = ZarrArchiveFactory.create(dandiset__owners=[user])

    resp = api_client.get(
        f'/api/zarr/{zarr_archive.zarr_id}/',
        {
            'name': zarr_archive.name,
            'dandiset': zarr_archive.dandiset.identifier,
        },
    )
    assert resp.status_code == 400
    assert resp.json() == ['Zarr already exists']
