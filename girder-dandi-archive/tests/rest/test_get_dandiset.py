import pytest
from pytest_girder.assertions import assertStatus, assertStatusOk
from rest_utils import assert_dandisets_are_equal

pytestmark = pytest.mark.plugin("dandi_archive")
path = "/dandi"


def test_get_dandiset(server, request_auth, dandiset_1):
    identifier = dandiset_1["name"]

    resp = server.request(
        path=path, method="GET", params={"identifier": identifier}, **request_auth
    )
    assertStatusOk(resp)

    assert_dandisets_are_equal(dandiset_1, resp.json)


def test_get_dandiset_does_not_exist(server, request_auth):
    resp = server.request(
        path=path, method="GET", params={"identifier": "000001"}, **request_auth
    )
    assertStatus(resp, 400)


def test_get_dandiset_no_identifier(server, request_auth, dandiset_1):
    resp = server.request(path=path, method="GET", params={}, **request_auth)
    assertStatus(resp, 400)


def test_get_dandiset_empty_identifier(server, request_auth, dandiset_1):
    resp = server.request(
        path=path, method="GET", params={"identifier": ""}, **request_auth,
    )
    assertStatus(resp, 400)


def test_get_dandiset_invalid_identifier(server, request_auth, dandiset_1):
    resp = server.request(
        path=path, method="GET", params={"identifier": "1"}, **request_auth
    )
    assertStatus(resp, 400)
