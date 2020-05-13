import json

import pytest

from pytest_girder.assertions import assertStatusOk

pytestmark = pytest.mark.plugin("dandi_archive")


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


def test_initial_dandiset_owners(server, admin_created_dandiset):
    """Assert that the list of owners isn't zero.

    The group members should always contain at least the dandiset creator.
    """
    identifier = admin_created_dandiset["meta"]["dandiset"]["identifier"]
    resp = server.request(path=f"/dandi/{identifier}/owners", method="GET")

    assertStatusOk(resp)
    assert len(resp.json) == 1


def test_add_dandiset_owners(server, admin, user, admin_created_dandiset):
    """Assert that adding a user to the list of owners produces the expected result."""
    identifier = admin_created_dandiset["meta"]["dandiset"]["identifier"]
    request_body = json.dumps([user], default=str)

    resp = server.request(
        path=f"/dandi/{identifier}/owners",
        method="PUT",
        body=request_body,
        user=admin,
        type="application/json",
    )

    users = resp.json
    assert len(users) == 2
    assert [new_user for new_user in users if new_user["id"] == str(user["_id"])]


def test_remove_dandiset_owners(server, admin, user, multi_owner_dandiset):
    """Assert that removing a user to the list of owners produces the expected result."""
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
