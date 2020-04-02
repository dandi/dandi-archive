import pytest

from girder.models.folder import Folder
from girder.models.upload import Upload
from pytest_girder.assertions import assertStatusOk

pytestmark = pytest.mark.plugin("dandi_archive")
path = "/dandi/stats"


def test_stats_zero(server):
    resp = server.request(path=path, method="GET")
    assertStatusOk(resp)
    assert {
        "draft_count": 0,
        "published_count": 0,
        "user_count": 0,
        "species_count": 0,
        "subject_count": 0,
        "cell_count": 0,
        "size": 0,
    } == resp.json


def test_stats_user(server, user):
    resp = server.request(path=path, method="GET")
    assertStatusOk(resp)
    assert {
        "draft_count": 0,
        "published_count": 0,
        "user_count": 2,  # one admin user, one normal user
        "species_count": 0,
        "subject_count": 0,
        "cell_count": 0,
        "size": 0,
    } == resp.json


def test_stats_draft(server, dandiset_1):
    resp = server.request(path=path, method="GET")
    assertStatusOk(resp)
    assert {
        "draft_count": 1,
        "published_count": 0,
        "user_count": 2,  # one admin user, one normal user, required by dandiset_1
        "species_count": 0,
        "subject_count": 0,
        "cell_count": 0,
        "size": 0,
    } == resp.json


def test_stats_species(server, dandiset_1):
    dandiset_1["meta"]["dandiset"]["organism"] = [{"species": "Homo Sapiens"}]
    Folder().setMetadata(dandiset_1, dandiset_1["meta"])

    resp = server.request(path=path, method="GET")
    assertStatusOk(resp)
    assert {
        "draft_count": 1,
        "published_count": 0,
        "user_count": 2,  # one admin user, one normal user, required by dandiset_1
        "species_count": 1,
        "subject_count": 0,
        "cell_count": 0,
        "size": 0,
    } == resp.json


def test_stats_two_species(server, dandiset_1):
    dandiset_1["meta"]["dandiset"]["organism"] = [
        {"species": "Homo Sapiens"},
        {"species": "Homo Erectus"},
    ]
    Folder().setMetadata(dandiset_1, dandiset_1["meta"])

    resp = server.request(path=path, method="GET")
    assertStatusOk(resp)
    assert {
        "draft_count": 1,
        "published_count": 0,
        "user_count": 2,  # one admin user, one normal user, required by dandiset_1
        "species_count": 2,
        "subject_count": 0,
        "cell_count": 0,
        "size": 0,
    } == resp.json


def test_stats_subjects(server, dandiset_1):
    subject_count = 7

    dandiset_1["meta"]["dandiset"]["number_of_subjects"] = subject_count
    Folder().setMetadata(dandiset_1, dandiset_1["meta"])

    resp = server.request(path=path, method="GET")
    assertStatusOk(resp)
    assert {
        "draft_count": 1,
        "published_count": 0,
        "user_count": 2,  # one admin user, one normal user, required by dandiset_1
        "species_count": 0,
        "subject_count": subject_count,
        "cell_count": 0,
        "size": 0,
    } == resp.json


def test_stats_cells(server, dandiset_1):
    cell_count = 11

    dandiset_1["meta"]["dandiset"]["number_of_cells"] = cell_count
    Folder().setMetadata(dandiset_1, dandiset_1["meta"])

    resp = server.request(path=path, method="GET")
    assertStatusOk(resp)
    assert {
        "draft_count": 1,
        "published_count": 0,
        "user_count": 2,  # one admin user, one normal user, required by dandiset_1
        "species_count": 0,
        "subject_count": 0,
        "cell_count": cell_count,
        "size": 0,
    } == resp.json


def test_stats_size(server, fsAssetstore, user, dandiset_1):  # NOQA
    file_contents = "Hello World!"
    upload = Upload().createUpload(
        user=user,
        name="helloworld.txt",
        parentType="folder",
        parent=dandiset_1,
        size=len(file_contents),
    )
    Upload().handleChunk(upload, file_contents)

    resp = server.request(path=path, method="GET")
    assertStatusOk(resp)
    assert {
        "draft_count": 1,
        "published_count": 0,
        "user_count": 2,  # one admin user, one normal user, required by dandiset_1
        "species_count": 0,
        "subject_count": 0,
        "cell_count": 0,
        "size": len(file_contents),
    } == resp.json
