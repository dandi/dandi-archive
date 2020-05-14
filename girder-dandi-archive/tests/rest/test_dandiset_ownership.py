import json

import pytest

from girder.constants import AccessType
from girder.models.user import User
from pytest_girder.assertions import assertStatus, assertStatusOk

pytestmark = pytest.mark.plugin("dandi_archive")


@pytest.fixture
def user_2(server):
    return User().createUser(
        email="user2@girder.test",
        login="user2",
        firstName="user2",
        lastName="user2",
        password="password",
        admin=False,
    )


@pytest.fixture
def admin_created_dandiset(server, admin):
    resp = server.request(
        path="/dandi",
        method="POST",
        user=admin,
        params={
            "name": "admin_created_dandiset",
            "description": "Admin created this test dandiset.",
        },
    )
    assertStatusOk(resp)
    return resp.json


@pytest.fixture
def multi_owner_dandiset(server, admin, user):
    resp = server.request(
        path="/dandi",
        method="POST",
        user=admin,
        params={
            "name": "multi_owner_dandiset",
            "description": "Dandiset that has multiple owners.",
        },
    )
    assertStatusOk(resp)

    created_dandiset = resp.json
    identifier = created_dandiset["meta"]["dandiset"]["identifier"]

    assertStatusOk(
        server.request(
            path=f"/dandi/{identifier}/owners",
            method="PUT",
            body=json.dumps([user], default=str),
            user=admin,
            type="application/json",
        )
    )

    return created_dandiset


def test_fixtures_independent(admin_created_dandiset, multi_owner_dandiset):
    assert admin_created_dandiset["_id"] != multi_owner_dandiset["_id"]


def test_initial_dandiset_owners(server, admin, admin_created_dandiset):
    """Assert that the list of owners isn't zero.

    The group members should always contain at least the dandiset creator.
    """
    identifier = admin_created_dandiset["meta"]["dandiset"]["identifier"]
    resp = server.request(path=f"/dandi/{identifier}/owners", method="GET")

    assertStatusOk(resp)
    assert len(resp.json) == 1
    assert resp.json[0]["id"] == str(admin["_id"])


def test_add_dandiset_owners(server, admin, user, admin_created_dandiset):
    """Assert that adding a user to the list of owners produces the expected result."""
    # Assert that user initially doesn't have permissions
    assertStatus(
        server.request(
            path=f"/folder/{admin_created_dandiset['_id']}/access", method="GET", user=user
        ),
        403,
    )

    identifier = admin_created_dandiset["meta"]["dandiset"]["identifier"]
    request_body = json.dumps([user], default=str)
    resp = server.request(
        path=f"/dandi/{identifier}/owners",
        method="PUT",
        body=request_body,
        user=admin,
        type="application/json",
    )
    assertStatusOk(resp)
    users = resp.json

    assert len(users) == 2
    assert [new_user for new_user in users if new_user["id"] == str(user["_id"])]

    # Assert that user now has permissions
    assertStatus(
        server.request(
            path=f"/folder/{admin_created_dandiset['_id']}/access", method="GET", user=user
        ),
        200,
    )


def test_remove_dandiset_owners(server, admin, user, multi_owner_dandiset):
    """Assert that removing a user to the list of owners produces the expected result."""
    # Assert that user initially has permissions
    assertStatus(
        server.request(
            path=f"/folder/{multi_owner_dandiset['_id']}/access", method="GET", user=user
        ),
        200,
    )

    identifier = multi_owner_dandiset["meta"]["dandiset"]["identifier"]
    request_body = json.dumps([user], default=str)
    resp = server.request(
        path=f"/dandi/{identifier}/owners",
        method="DELETE",
        body=request_body,
        user=admin,
        type="application/json",
    )

    users = resp.json
    assert len(users) == 1
    assert not [new_user for new_user in users if new_user["id"] == str(user["_id"])]

    # Assert that now user doesn't have permissions
    assertStatus(
        server.request(
            path=f"/folder/{multi_owner_dandiset['_id']}/access", method="GET", user=user
        ),
        403,
    )


def test_user_removed_from_owners(server, user, user_2, admin, admin_created_dandiset):
    """Test that an existing user without admin permissions has none after another user is added."""
    access_param = json.dumps(
        {"users": [{"id": user["_id"], "level": AccessType.WRITE}]}, default=str
    )
    assertStatusOk(
        server.request(
            path=f"/folder/{admin_created_dandiset['_id']}/access",
            method="PUT",
            user=admin,
            params={"access": access_param},
        )
    )

    resp = server.request(
        path=f"/folder/{admin_created_dandiset['_id']}/access", method="GET", user=admin,
    )
    assertStatusOk(resp)
    assert len(resp.json["users"]) == 1
    assert resp.json["users"][0]["id"] == str(user["_id"])

    identifier = admin_created_dandiset["meta"]["dandiset"]["identifier"]
    request_body = json.dumps([user_2], default=str)
    resp = server.request(
        path=f"/dandi/{identifier}/owners",
        method="PUT",
        body=request_body,
        user=admin,
        type="application/json",
    )

    assertStatusOk(resp)
    assert len(resp.json) == 1
    assert resp.json[0]["id"] != str(user["_id"])
    assert resp.json[0]["id"] == str(user_2["_id"])
    assertStatus(
        server.request(
            path=f"/folder/{admin_created_dandiset['_id']}/access", method="GET", user=user,
        ),
        403,
    )


def test_user_promoted_to_owner(server, user, user_2, admin, admin_created_dandiset):
    """Test that an existing user without admin permissions has admin after that user is added."""
    access_param = json.dumps(
        {"users": [{"id": user["_id"], "level": AccessType.WRITE}]}, default=str
    )
    assertStatusOk(
        server.request(
            path=f"/folder/{admin_created_dandiset['_id']}/access",
            method="PUT",
            user=admin,
            params={"access": access_param},
        )
    )

    resp = server.request(
        path=f"/folder/{admin_created_dandiset['_id']}/access", method="GET", user=admin,
    )
    assertStatusOk(resp)
    assert len(resp.json["users"]) == 1
    assert resp.json["users"][0]["id"] == str(user["_id"])

    # Add user to owners, which should promote existing WRITE permission to ADMIN
    identifier = admin_created_dandiset["meta"]["dandiset"]["identifier"]
    resp = server.request(
        path=f"/dandi/{identifier}/owners",
        method="PUT",
        body=json.dumps([user], default=str),
        user=admin,
        type="application/json",
    )

    assertStatusOk(resp)
    assert len(resp.json) == 1
    assert resp.json[0]["id"] == str(user["_id"])
    assert resp.json[0]["level"] == AccessType.ADMIN
    assertStatusOk(
        server.request(
            path=f"/folder/{admin_created_dandiset['_id']}/access", method="GET", user=user,
        ),
    )
