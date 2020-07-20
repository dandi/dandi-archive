import pytest

from pytest_girder.assertions import assertStatus, assertStatusOk


pytestmark = pytest.mark.plugin("dandi_archive")


def mkfolder(server, request_auth, name, parent_id):
    resp = server.request(
        "/folder",
        method="POST",
        params={"parentType": "folder", "parentId": parent_id, "name": name},
        **request_auth,
    )
    assertStatusOk(resp)
    return resp.json["_id"]


def mkitem(server, request_auth, name, folder_id):
    resp = server.request(
        "/item", method="POST", params={"folderId": folder_id, "name": name}, **request_auth,
    )
    assertStatusOk(resp)
    return resp.json["_id"]


def mkfile(server, request_auth, name, item_id, content):
    resp = server.request(
        "/file",
        method="POST",
        params={
            "parentType": "item",
            "parentId": item_id,
            "name": name,
            "mimeType": "text/plain",
            "size": len(content),
        },
        body=content,
        type="text/plain",
        isJson=False,
        **request_auth,
    )
    assertStatusOk(resp)


def test_get_dandiset_stats_zero(server, dandiset_1):
    identifier = dandiset_1["name"]
    resp = server.request(f"/dandi/{identifier}/stats", method="GET")
    assertStatusOk(resp)
    assert {"bytes": 0, "folders": 0, "items": 0} == resp.json


def test_get_dandiset_stats_one_folder(server, dandiset_1, request_auth):
    dandi_id = dandiset_1["_id"]
    identifier = dandiset_1["name"]
    mkfolder(server, request_auth, "Test Folder", dandi_id)
    resp = server.request(f"/dandi/{identifier}/stats", method="GET")
    assertStatusOk(resp)
    assert {"bytes": 0, "folders": 1, "items": 0} == resp.json


def test_get_dandiset_stats_one_item(server, dandiset_1, request_auth):
    dandi_id = dandiset_1["_id"]
    identifier = dandiset_1["name"]
    mkitem(server, request_auth, "Test Item", dandi_id)
    resp = server.request(f"/dandi/{identifier}/stats", method="GET")
    assertStatusOk(resp)
    assert {"bytes": 0, "folders": 0, "items": 1} == resp.json


def test_get_dandiset_stats_one_file(server, dandiset_1, request_auth, fsAssetstore):  # noqa: N803
    dandi_id = dandiset_1["_id"]
    identifier = dandiset_1["name"]
    item_id = mkitem(server, request_auth, "Test Item", dandi_id)
    content = "This is test text."
    mkfile(server, request_auth, "foo.txt", item_id, content)
    resp = server.request(f"/dandi/{identifier}/stats", method="GET")
    assertStatusOk(resp)
    assert {"bytes": len(content), "folders": 0, "items": 1} == resp.json


def test_get_dandiset_stats_tree(server, dandiset_1, request_auth, fsAssetstore):  # noqa: N803
    dandi_id = dandiset_1["_id"]
    identifier = dandiset_1["name"]

    folder_a_id = mkfolder(server, request_auth, "Folder A", dandi_id)
    folder_b_id = mkfolder(server, request_auth, "Folder B", folder_a_id)
    folder_c_id = mkfolder(server, request_auth, "Folder C", folder_b_id)  # noqa: F841
    folder_d_id = mkfolder(server, request_auth, "Folder D", folder_b_id)

    item_a_id = mkitem(server, request_auth, "Item A", dandi_id)
    item_b_id = mkitem(server, request_auth, "Item B", folder_a_id)
    item_c_id = mkitem(server, request_auth, "Item C", folder_d_id)  # noqa: F841

    contents = [
        "This is test text.",
        "Lorem ipsum dolor sit amet",
        "'Twas brillig, and the slithy toves did gyre and gimble in the wabe.",
    ]

    mkfile(server, request_auth, "test.txt", item_a_id, contents[0])
    mkfile(server, request_auth, "lorem.txt", item_b_id, contents[1])
    mkfile(server, request_auth, "jabberwocky.txt", item_b_id, contents[2])

    resp = server.request(f"/dandi/{identifier}/stats", method="GET")
    assertStatusOk(resp)
    assert {"bytes": len("".join(contents)), "folders": 4, "items": 3} == resp.json


def test_get_dandiset_stats_does_not_exist(server, request_auth):
    resp = server.request(path="/dandi/000001/stats", method="GET", **request_auth)
    assertStatus(resp, 400)
