import pytest
from pytest_girder.assertions import assertStatus, assertStatusOk
from rest_utils import assert_dandisets_are_equal

pytestmark = pytest.mark.plugin("dandi_archive")


def test_get_dandiset(server, request_auth, dandiset_1):
    identifier = dandiset_1["name"]

    resp = server.request(path="/dandi/" + identifier, method="GET", **request_auth,)
    assertStatusOk(resp)

    assert_dandisets_are_equal(dandiset_1, resp.json)


def test_get_dandiset_does_not_exist(server, request_auth):
    resp = server.request(path="/dandi/000001", method="GET", **request_auth)
    assertStatus(resp, 400)


def test_get_dandiset_invalid_identifier(server, request_auth, dandiset_1):
    resp = server.request(path="/dandi/x", method="GET", **request_auth)
    assertStatus(resp, 400)
