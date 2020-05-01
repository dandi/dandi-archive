import pytest
from rest_utils import assert_dandisets_are_equal, DESCRIPTION_2, NAME_1

from pytest_girder.assertions import assertStatusOk

pytestmark = pytest.mark.plugin("dandi_archive")
path = "/dandi/search"


def test_search_dandisets(server, request_auth, dandiset_1, dandiset_2):
    resp = server.request(path=path, method="GET", params={"search": ""}, **request_auth)
    assertStatusOk(resp)
    assert len(resp.json) == 2
    assert_dandisets_are_equal(dandiset_1, resp.json[0])
    assert_dandisets_are_equal(dandiset_2, resp.json[1])


def test_search_dandisets_name(server, request_auth, dandiset_1, dandiset_2):
    resp = server.request(path=path, method="GET", params={"search": NAME_1}, **request_auth)
    assertStatusOk(resp)
    assert len(resp.json) == 1
    assert_dandisets_are_equal(dandiset_1, resp.json[0])


def test_search_dandisets_description_partial(server, request_auth, dandiset_1, dandiset_2):
    resp = server.request(
        path=path, method="GET", params={"search": DESCRIPTION_2[:5]}, **request_auth
    )
    assertStatusOk(resp)
    assert len(resp.json) == 1
    assert_dandisets_are_equal(dandiset_2, resp.json[0])
