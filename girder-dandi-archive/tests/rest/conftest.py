import pytest

from pytest_girder.assertions import assertStatusOk

from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.token import Token, TokenScope

from girder_dandi_archive.util import get_or_create_drafts_collection


from rest_utils import NAME_1, DESCRIPTION_1, NAME_2, DESCRIPTION_2


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
