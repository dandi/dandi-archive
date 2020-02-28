from girder.api import access
from girder.api.rest import Resource
from girder.api.describe import describeRoute, Description
from girder.models.setting import Setting
from girder.models.folder import Folder
from girder.exceptions import RestException

from .util import (
    DANDISET_ID_COUNTER,
    DANDISET_ID_LENGTH,
    staging_collection,
    validate_dandiset_id,
)


class DandiResource(Resource):
    def __init__(self):
        super(DandiResource, self).__init__()

        self.resourceName = "dandi"
        self.route("GET", (), self.get_dandiset)
        self.route("POST", (), self.create_dandiset)

    @access.user
    @describeRoute(
        Description("Create Dandiset")
        .param("name", "Name of the Dandiset.")
        .param("description", "Description of the Dandiset.")
    )
    def create_dandiset(self, params):
        if "name" not in params or "description" not in params:
            raise RestException("Name and description required.")

        name, description = params["name"], params["description"]

        if not name or not description:
            raise RestException("Name and description must not be empty.")

        exists = Folder().findOne({"name": name})

        if exists:
            raise RestException("Dandiset already exists", code=409)

        current = Setting().get(DANDISET_ID_COUNTER)
        if current is None:
            current = -1

        new_id_count = Setting().set(DANDISET_ID_COUNTER, current + 1)["value"]
        padded_id = f"{new_id_count:0{DANDISET_ID_LENGTH}d}"
        meta = {"name": name, "description": description, "id": padded_id}

        staging = staging_collection()
        folder = Folder().createFolder(
            staging, name, parentType="collection", creator=self.getCurrentUser(),
        )
        folder = Folder().setMetadata(folder, {"dandiset": meta})
        return folder

    @access.public
    @describeRoute(Description("Get Dandiset").param("id", "Dandiset ID"))
    def get_dandiset(self, params):
        if not validate_dandiset_id(params["id"]):
            raise RestException("Invalid Dandiset ID")

        doc = Folder().findOne({"meta.dandiset.id": params["id"]})
        return doc
