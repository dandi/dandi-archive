from __future__ import annotations

from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.services.embargo import AssetBlobEmbargoedError, remove_asset_blob_embargoed_tag
from dandiapi.api.tasks.scheduled import send_dandisets_to_unembargo_email


@pytest.mark.django_db()
def test_remove_asset_blob_embargoed_tag_fails_on_embargod(embargoed_asset_blob, asset_blob):
    with pytest.raises(AssetBlobEmbargoedError):
        remove_asset_blob_embargoed_tag(embargoed_asset_blob)

    # Test that error not raised on non-embargoed asset blob
    remove_asset_blob_embargoed_tag(asset_blob)


@pytest.mark.django_db()
def test_unembargo_dandiset_sends_emails(
    api_client, user, dandiset, draft_version_factory, mailoutbox
):
    draft_version_factory(dandiset=dandiset)

    assign_perm('owner', user, dandiset)
    api_client.force_authenticate(user=user)

    dandiset.embargo_status = Dandiset.EmbargoStatus.EMBARGOED
    dandiset.save()

    resp = api_client.post(f'/api/dandisets/{dandiset.identifier}/unembargo/')
    assert resp.status_code == 200

    # Simulate the scheduled task calling this function
    send_dandisets_to_unembargo_email()

    assert mailoutbox
    assert 'un-embargo' in mailoutbox[0].subject
    assert dandiset.identifier in mailoutbox[0].message().get_payload()
    assert user.username in mailoutbox[0].message().get_payload()
