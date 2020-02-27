from girder.api import access
from girder.api.rest import Resource
from girder.api.describe import describeRoute, Description
from girder.models.setting import Setting
from girder.models.folder import Folder
from girder.exceptions import RestException

from .util import DANDI_ID_COUNTER, staging_collection, pad_dandi_id, validate_dandi_id


@access.user
@describeRoute(
    Description("Create Dandiset")
    .param("name", "Name of the Dandiset.")
    .param("description", "Description of the Dandiset.")
)
def create_dandiset(params):
    name, description = params["name"], params["description"]
    exists = Folder().findOne({"name": name})

    if exists:
        raise RestException("Dandiset already exists", code=409)

    current = Setting().get(DANDI_ID_COUNTER)
    if current is None:
        new_id_count = Setting().set(DANDI_ID_COUNTER, 0)
    else:
        new_id_count = Setting().set(DANDI_ID_COUNTER, current + 1)

    padded_id = pad_dandi_id(new_id_count["value"])
    meta = {"name": name, "description": description, "id": padded_id}

    staging = staging_collection()
    folder = Folder().createFolder(
        staging, name, parentType="collection", public=False,
    )
    folder = Folder().setMetadata(folder, {"dandiset": meta})
    return folder


@access.public
@describeRoute(Description("Get Dandiset").param("id", "Dandiset ID"))
def get_dandiset(params):
    if not validate_dandi_id(params["id"]):
        raise RestException("Invalid Dandiset ID")

    doc = Folder().findOne({"meta.dandiset.id": params["id"]})
    return doc


class DandiResource(Resource):
    def __init__(self):
        super(DandiResource, self).__init__()

        self.resourceName = "dandi"
        self.route("GET", (), get_dandiset)
        self.route("POST", (), create_dandiset)
