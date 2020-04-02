import pytest
from rest_utils import assert_dandisets_are_equal

from pytest_girder.assertions import assertStatusOk

pytestmark = pytest.mark.plugin("dandi_archive")
path = "/dandi"


def test_list_dandisets(server, request_auth, dandiset_1, dandiset_2):
    resp = server.request(path=path, method="GET", **request_auth)
    assertStatusOk(resp)
    assert len(resp.json) == 2
    assert_dandisets_are_equal(dandiset_1, resp.json[0])
    assert_dandisets_are_equal(dandiset_2, resp.json[1])


def test_list_dandisets_sort(server, request_auth, dandiset_1, dandiset_2):
    resp = server.request(
        path=path,
        method="GET",
        params={"sort": "meta.dandiset.description"},
        **request_auth,
    )
    assertStatusOk(resp)
    assert len(resp.json) == 2
    assert_dandisets_are_equal(dandiset_2, resp.json[0])
    assert_dandisets_are_equal(dandiset_1, resp.json[1])


def test_list_dandisets_limit(server, request_auth, dandiset_1, dandiset_2):
    resp = server.request(path=path, method="GET", params={"limit": 1}, **request_auth)
    assertStatusOk(resp)
    assert len(resp.json) == 1
    assert_dandisets_are_equal(dandiset_1, resp.json[0])


def test_list_dandisets_offset(server, request_auth, dandiset_1, dandiset_2):
    resp = server.request(
        path=path, method="GET", params={"limit": 1, "offset": 1}, **request_auth,
    )
    assertStatusOk(resp)
    assert len(resp.json) == 1
    assert_dandisets_are_equal(dandiset_2, resp.json[0])
