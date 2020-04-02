import pytest
from rest_utils import (
    assert_dandisets_are_equal,
    DESCRIPTION_1,
    DESCRIPTION_2,
    NAME_1,
    NAME_2,
)

from pytest_girder.assertions import assertStatus, assertStatusOk


pytestmark = pytest.mark.plugin("dandi_archive")
path = "/dandi"


def test_create_dandiset(server, request_auth, drafts_collection, user):
    drafts_collection_id = str(drafts_collection["_id"])
    user_id = str(user["_id"])

    resp = server.request(
        path=path,
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
        path=path,
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
        path=path, method="POST", params={"description": DESCRIPTION_1}, **request_auth,
    )
    assertStatus(resp, 400)


def test_create_dandiset_no_description(server, request_auth):
    resp = server.request(
        path=path, method="POST", params={"name": NAME_1}, **request_auth
    )
    assertStatus(resp, 400)


def test_create_dandiset_empty_name(server, request_auth):
    resp = server.request(
        path=path,
        method="POST",
        params={"name": "", "description": DESCRIPTION_1},
        **request_auth,
    )
    assertStatus(resp, 400)


def test_create_dandiset_empty_description(server, request_auth):
    resp = server.request(
        path=path,
        method="POST",
        params={"name": NAME_1, "description": ""},
        **request_auth,
    )
    assertStatus(resp, 400)
