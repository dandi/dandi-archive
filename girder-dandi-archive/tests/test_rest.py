import pytest

from girder_dandi_archive.util import get_or_create_drafts_collection

from girder.models.collection import Collection
from girder.models.folder import Folder

from pytest_girder.assertions import assertStatus, assertStatusOk

pytestmark = pytest.mark.plugin("dandi_archive")

NAME_1 = "test dandiset 1 name"
DESCRIPTION_1 = "test dandiset 1 description"
NAME_2 = "test dandiset 2 name"
DESCRIPTION_2 = "test dandiset 2 description"


@pytest.fixture
def drafts_folders(db):
    red_herring_collection = Collection().createCollection(
        "red_herring_collection", reuseExisting=True
    )
    # A folder that matches dandiset metadata, but not in drafts collection.
    red_herring_dandiset_000001_folder = Folder().createFolder(
        parent=red_herring_collection,
        parentType="collection",
        name="000001",
        public=True,
    )
    meta = {
        "dandiset": {"name": "red", "description": "herring", "identifier": "000001"}
    }
    Folder().setMetadata(red_herring_dandiset_000001_folder, meta)
    return_dict = {
        "red_herring_collection": red_herring_collection,
        "red_herring_folder": red_herring_dandiset_000001_folder,
    }
    return_dict["drafts_collection"] = get_or_create_drafts_collection()
    yield return_dict


@pytest.fixture
def dandiset_1(server, drafts_folders, user):
    resp = server.request(
        path="/dandi",
        method="POST",
        user=user,
        params={"name": NAME_1, "description": DESCRIPTION_1},
    )
    assertStatusOk(resp)
    yield resp.json


@pytest.fixture
def dandiset_2(server, drafts_folders, user):
    resp = server.request(
        path="/dandi",
        method="POST",
        user=user,
        params={"name": NAME_2, "description": DESCRIPTION_2},
    )
    assertStatusOk(resp)
    yield resp.json


def test_create_dandiset(server, drafts_folders, user):
    drafts_collection_id = str(drafts_folders["drafts_collection"]["_id"])
    user_id = str(user["_id"])

    resp = server.request(
        path="/dandi",
        method="POST",
        user=user,
        params={"name": NAME_1, "description": DESCRIPTION_1},
    )
    assertStatusOk(resp)

    assert resp.json["access"] == {
        "groups": [],
        "users": [{"flags": [], "id": user_id, "level": 2}],
    }
    assert resp.json["baseParentId"] == drafts_collection_id
    assert resp.json["baseParentType"] == "collection"
    assert resp.json["creatorId"] == user_id
    assert resp.json["description"] == ""
    assert resp.json["lowerName"] == "000001"
    assert resp.json["meta"] == {
        "dandiset": {
            "identifier": "000001",
            "name": NAME_1,
            "description": DESCRIPTION_1,
        }
    }
    assert resp.json["name"] == "000001"
    assert resp.json["parentCollection"] == "collection"
    assert resp.json["parentId"] == drafts_collection_id
    assert resp.json["public"] is True
    assert resp.json["size"] == 0


def test_create_two_dandisets(server, drafts_folders, user, dandiset_1):
    drafts_collection_id = str(drafts_folders["drafts_collection"]["_id"])
    user_id = str(user["_id"])

    resp = server.request(
        path="/dandi",
        method="POST",
        user=user,
        params={"name": NAME_2, "description": DESCRIPTION_2},
    )
    assertStatusOk(resp)

    assert resp.json["access"] == {
        "groups": [],
        "users": [{"flags": [], "id": user_id, "level": 2}],
    }
    assert resp.json["baseParentId"] == drafts_collection_id
    assert resp.json["baseParentType"] == "collection"
    assert resp.json["creatorId"] == user_id
    assert resp.json["description"] == ""
    assert resp.json["lowerName"] == "000002"
    assert resp.json["meta"] == {
        "dandiset": {
            "identifier": "000002",
            "name": NAME_2,
            "description": DESCRIPTION_2,
        }
    }
    assert resp.json["name"] == "000002"
    assert resp.json["parentCollection"] == "collection"
    assert resp.json["parentId"] == drafts_collection_id
    assert resp.json["public"] is True
    assert resp.json["size"] == 0


def test_create_dandiset_no_name(server, drafts_folders, user):
    resp = server.request(
        path="/dandi", method="POST", user=user, params={"description": DESCRIPTION_1},
    )
    assertStatus(resp, 400)


def test_create_dandiset_no_description(server, drafts_folders, user):
    resp = server.request(
        path="/dandi", method="POST", user=user, params={"name": NAME_1},
    )
    assertStatus(resp, 400)


def test_create_dandiset_empty_name(server, drafts_folders, user):
    resp = server.request(
        path="/dandi",
        method="POST",
        user=user,
        params={"name": "", "description": DESCRIPTION_1},
    )
    assertStatus(resp, 400)


def test_create_dandiset_empty_description(server, drafts_folders, user):
    resp = server.request(
        path="/dandi",
        method="POST",
        user=user,
        params={"name": NAME_1, "description": ""},
    )
    assertStatus(resp, 400)


def test_get_dandiset(server, drafts_folders, user, dandiset_1):
    identifier = dandiset_1["name"]
    drafts_collection_id = str(drafts_folders["drafts_collection"]["_id"])
    user_id = str(user["_id"])

    # Ensure we can retrieve the Dandiset.
    resp = server.request(
        path="/dandi", method="GET", user=user, params={"identifier": identifier}
    )
    assertStatusOk(resp)

    assert resp.json["access"] == {
        "groups": [],
        "users": [{"flags": [], "id": user_id, "level": 2}],
    }
    assert resp.json["baseParentId"] == drafts_collection_id
    assert resp.json["baseParentType"] == "collection"
    assert resp.json["creatorId"] == user_id
    assert resp.json["description"] == ""
    assert resp.json["lowerName"] == "000001"
    assert resp.json["meta"] == {
        "dandiset": {
            "identifier": "000001",
            "name": NAME_1,
            "description": DESCRIPTION_1,
        }
    }
    assert resp.json["name"] == "000001"
    assert resp.json["parentCollection"] == "collection"
    assert resp.json["parentId"] == drafts_collection_id
    assert resp.json["public"] is True
    assert resp.json["size"] == 0


def test_get_dandiset_does_not_exist(server, drafts_folders, user):
    resp = server.request(
        path="/dandi", method="GET", user=user, params={"identifier": "000001"}
    )
    assertStatus(resp, 400)


def test_get_dandiset_no_identifier(server, drafts_folders, user, dandiset_1):
    resp = server.request(path="/dandi", method="GET", user=user, params={})
    assertStatus(resp, 400)


def test_get_dandiset_empty_identifier(server, drafts_folders, user, dandiset_1):
    resp = server.request(
        path="/dandi", method="GET", user=user, params={"identifier": ""}
    )
    assertStatus(resp, 400)


def test_get_dandiset_invalid_identifier(server, drafts_folders, user, dandiset_1):
    resp = server.request(
        path="/dandi", method="GET", user=user, params={"identifier": "1"}
    )
    assertStatus(resp, 400)
