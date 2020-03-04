import pytest

from girder_dandi_archive.util import create_drafts_collection

from girder.models.collection import Collection
from girder.models.folder import Folder

from pytest_girder.assertions import assertStatus, assertStatusOk


@pytest.fixture
def draftsFolders(db):
    red_herring_collection = Collection().createCollection(
        "red_herring_collection", reuseExisting=True
    )
    # A folder that matches dandiset metadata, but not in drafts collection.
    red_herring_dandiset_000000_folder = Folder().createFolder(
        parent=red_herring_collection,
        parentType="collection",
        name="000000",
        public=True,
    )
    meta = {
        "dandiset": {
            "name": "red",
            "description": "herring",
            "identifier": "000000",
            "version": "draft",
        }
    }
    Folder().setMetadata(red_herring_dandiset_000000_folder, meta)
    return_dict = {
        "red_herring_collection": red_herring_collection,
        "red_herring_folder": red_herring_dandiset_000000_folder,
    }
    return_dict["drafts_collection"] = create_drafts_collection()
    yield return_dict


@pytest.mark.plugin("dandi_archive")
def testCreateDandiset(server, draftsFolders, user):
    drafts_collection_id = str(draftsFolders["drafts_collection"]["_id"])

    resp = server.request(
        path="/dandi",
        method="POST",
        user=user,
        params={
            "name": "test dandiset 0 name",
            "description": "test dandiset 0 description",
        },
    )
    assertStatusOk(resp)
    test_dandiset_0_folder = resp.json
    test_dandiset_0_folder_meta = test_dandiset_0_folder["meta"]["dandiset"]

    assert drafts_collection_id == test_dandiset_0_folder["parentId"]
    assert "000000" == test_dandiset_0_folder["name"]
    assert "000000" == test_dandiset_0_folder_meta["identifier"]
    assert "test dandiset 0 name" == test_dandiset_0_folder_meta["name"]
    assert "test dandiset 0 description" == test_dandiset_0_folder_meta["description"]
    assert "draft" == test_dandiset_0_folder_meta["version"]

    resp = server.request(
        path="/dandi",
        method="POST",
        user=user,
        params={
            "name": "test dandiset 1 name",
            "description": "test dandiset 1 description",
        },
    )
    assertStatusOk(resp)
    test_dandiset_1_folder = resp.json
    test_dandiset_1_folder_meta = test_dandiset_1_folder["meta"]["dandiset"]

    assert drafts_collection_id == test_dandiset_1_folder["parentId"]
    assert "000001" == test_dandiset_1_folder["name"]
    assert "000001" == test_dandiset_1_folder_meta["identifier"]
    assert "test dandiset 1 name" == test_dandiset_1_folder_meta["name"]
    assert "test dandiset 1 description" == test_dandiset_1_folder_meta["description"]
    assert "draft" == test_dandiset_1_folder_meta["version"]


@pytest.mark.plugin("dandi_archive")
def testGetDandiset(server, draftsFolders, user, capsys):
    drafts_collection_id = str(draftsFolders["drafts_collection"]["_id"])

    # Ensure we don't find any before creation, in the wrong parent.
    resp = server.request(
        path="/dandi",
        method="GET",
        user=user,
        params={"identifier": "000000", "version": "draft"},
    )
    assertStatusOk(resp)
    assert resp.json == {}

    # Create a Dandiset.
    resp = server.request(
        path="/dandi",
        method="POST",
        user=user,
        params={
            "name": "test dandiset 0 name",
            "description": "test dandiset 0 description",
        },
    )
    assertStatusOk(resp)
    assert "000000" == resp.json["meta"]["dandiset"]["identifier"]

    # Ensure we can retrieve the Dandiset.
    resp = server.request(
        path="/dandi",
        method="GET",
        user=user,
        params={"identifier": "000000", "version": "draft"},
    )
    assertStatusOk(resp)
    test_dandiset_0_folder = resp.json
    test_dandiset_0_folder_meta = test_dandiset_0_folder["meta"]["dandiset"]
    assert drafts_collection_id == test_dandiset_0_folder["parentId"]
    assert "000000" == test_dandiset_0_folder["name"]
    assert "000000" == test_dandiset_0_folder_meta["identifier"]
    assert "test dandiset 0 name" == test_dandiset_0_folder_meta["name"]
    assert "test dandiset 0 description" == test_dandiset_0_folder_meta["description"]
    assert "draft" == test_dandiset_0_folder_meta["version"]
