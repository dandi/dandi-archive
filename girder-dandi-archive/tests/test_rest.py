import pytest

from girder_dandi_archive.util import get_or_create_drafts_collection

from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.token import Token, TokenScope

from pytest_girder.assertions import assertStatus, assertStatusOk

pytestmark = pytest.mark.plugin("dandi_archive")

NAME_1 = "test dandiset 1 name"
DESCRIPTION_1 = "Zzzz! This sorts last."
NAME_2 = "test dandiset 2 name"
DESCRIPTION_2 = "Aaaa! This sorts first."


@pytest.fixture
def read_write_token(user):
    return Token().createToken(
        user, scope=[TokenScope.DATA_READ, TokenScope.DATA_WRITE]
    )


@pytest.fixture(params=["user", "read_write_token"])
def request_auth(request, user, read_write_token):
    if request.param == "user":
        return {"user": user}
    elif request.param == "read_write_token":
        return {"token": read_write_token}


@pytest.fixture(autouse=True)
def drafts_collection(db):
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

    return get_or_create_drafts_collection()


@pytest.fixture
def dandiset_1(server, request_auth):
    resp = server.request(
        path="/dandi",
        method="POST",
        params={"name": NAME_1, "description": DESCRIPTION_1},
        **request_auth,
    )
    assertStatusOk(resp)
    return resp.json


@pytest.fixture
def dandiset_2(server, request_auth):
    resp = server.request(
        path="/dandi",
        method="POST",
        params={"name": NAME_2, "description": DESCRIPTION_2},
        **request_auth,
    )
    assertStatusOk(resp)
    return resp.json


def assert_dandisets_are_equal(expected, actual):
    assert expected["access"] == actual["access"]
    assert expected["baseParentId"] == actual["baseParentId"]
    assert expected["baseParentType"] == actual["baseParentType"]
    # TODO created datetime
    assert expected["creatorId"] == actual["creatorId"]
    assert expected["description"] == actual["description"]
    assert expected["lowerName"] == actual["lowerName"]
    assert expected["meta"] == actual["meta"]
    assert expected["name"] == actual["name"]
    assert expected["parentCollection"] == actual["parentCollection"]
    assert expected["parentId"] == actual["parentId"]
    assert expected["public"] == actual["public"]
    assert expected["size"] == actual["size"]
    # TODO updated datetime


def test_create_dandiset(server, request_auth, drafts_collection, user):
    drafts_collection_id = str(drafts_collection["_id"])
    user_id = str(user["_id"])

    resp = server.request(
        path="/dandi",
        method="POST",
        params={"name": NAME_1, "description": DESCRIPTION_1},
        **request_auth,
    )
    assertStatusOk(resp)

    assert_dandisets_are_equal(
        {
            "access": {
                "groups": [],
                "users": [{"flags": [], "id": user_id, "level": 2}],
            },
            "baseParentId": drafts_collection_id,
            "baseParentType": "collection",
            # TODO created datetime
            "creatorId": user_id,
            "description": "",
            "lowerName": "000001",
            "meta": {
                "dandiset": {
                    "identifier": "000001",
                    "name": NAME_1,
                    "description": DESCRIPTION_1,
                }
            },
            "name": "000001",
            "parentCollection": "collection",
            "parentId": drafts_collection_id,
            "public": True,
            "size": 0,
            # TODO updated datetime
        },
        resp.json,
    )


def test_create_two_dandisets(
    server, request_auth, drafts_collection, user, dandiset_1
):
    drafts_collection_id = str(drafts_collection["_id"])
    user_id = str(user["_id"])

    resp = server.request(
        path="/dandi",
        method="POST",
        params={"name": NAME_2, "description": DESCRIPTION_2},
        **request_auth,
    )
    assertStatusOk(resp)

    assert_dandisets_are_equal(
        {
            "access": {
                "groups": [],
                "users": [{"flags": [], "id": user_id, "level": 2}],
            },
            "baseParentId": drafts_collection_id,
            "baseParentType": "collection",
            # TODO created datetime
            "creatorId": user_id,
            "description": "",
            "lowerName": "000002",
            "meta": {
                "dandiset": {
                    "identifier": "000002",
                    "name": NAME_2,
                    "description": DESCRIPTION_2,
                }
            },
            "name": "000002",
            "parentCollection": "collection",
            "parentId": drafts_collection_id,
            "public": True,
            "size": 0,
            # TODO updated datetime
        },
        resp.json,
    )


def test_create_dandiset_no_name(server, request_auth):
    resp = server.request(
        path="/dandi",
        method="POST",
        params={"description": DESCRIPTION_1},
        **request_auth,
    )
    assertStatus(resp, 400)


def test_create_dandiset_no_description(server, request_auth):
    resp = server.request(
        path="/dandi", method="POST", params={"name": NAME_1}, **request_auth
    )
    assertStatus(resp, 400)


def test_create_dandiset_empty_name(server, request_auth):
    resp = server.request(
        path="/dandi",
        method="POST",
        params={"name": "", "description": DESCRIPTION_1},
        **request_auth,
    )
    assertStatus(resp, 400)


def test_create_dandiset_empty_description(server, request_auth):
    resp = server.request(
        path="/dandi",
        method="POST",
        params={"name": NAME_1, "description": ""},
        **request_auth,
    )
    assertStatus(resp, 400)


def test_get_dandiset(server, request_auth, dandiset_1):
    identifier = dandiset_1["name"]

    resp = server.request(
        path="/dandi", method="GET", params={"identifier": identifier}, **request_auth
    )
    assertStatusOk(resp)

    assert_dandisets_are_equal(dandiset_1, resp.json)


def test_get_dandiset_does_not_exist(server, request_auth):
    resp = server.request(
        path="/dandi", method="GET", params={"identifier": "000001"}, **request_auth
    )
    assertStatus(resp, 400)


def test_get_dandiset_no_identifier(server, request_auth, dandiset_1):
    resp = server.request(path="/dandi", method="GET", params={}, **request_auth)
    assertStatus(resp, 400)


def test_get_dandiset_empty_identifier(server, request_auth, dandiset_1):
    resp = server.request(
        path="/dandi", method="GET", params={"identifier": ""}, **request_auth,
    )
    assertStatus(resp, 400)


def test_get_dandiset_invalid_identifier(server, request_auth, dandiset_1):
    resp = server.request(
        path="/dandi", method="GET", params={"identifier": "1"}, **request_auth
    )
    assertStatus(resp, 400)


def test_list_dandisets(server, request_auth, dandiset_1, dandiset_2):
    resp = server.request(path="/dandi/list", method="GET", **request_auth)
    assertStatusOk(resp)
    assert len(resp.json) == 2
    assert_dandisets_are_equal(dandiset_1, resp.json[0])
    assert_dandisets_are_equal(dandiset_2, resp.json[1])


def test_list_dandisets_sort(server, request_auth, dandiset_1, dandiset_2):
    resp = server.request(
        path="/dandi/list",
        method="GET",
        params={"sort": "meta.dandiset.description"},
        **request_auth,
    )
    assertStatusOk(resp)
    assert len(resp.json) == 2
    assert_dandisets_are_equal(dandiset_2, resp.json[0])
    assert_dandisets_are_equal(dandiset_1, resp.json[1])


def test_list_dandisets_limit(server, request_auth, dandiset_1, dandiset_2):
    resp = server.request(
        path="/dandi/list", method="GET", params={"limit": 1}, **request_auth
    )
    assertStatusOk(resp)
    assert len(resp.json) == 1
    assert_dandisets_are_equal(dandiset_1, resp.json[0])


def test_list_dandisets_offset(server, request_auth, dandiset_1, dandiset_2):
    resp = server.request(
        path="/dandi/list",
        method="GET",
        params={"limit": 1, "offset": 1},
        **request_auth,
    )
    assertStatusOk(resp)
    assert len(resp.json) == 1
    assert_dandisets_are_equal(dandiset_2, resp.json[0])
