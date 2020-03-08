from girder.api import access
from girder.api.rest import Resource
from girder.api.describe import describeRoute, Description
from girder.models.setting import Setting
from girder.models.folder import Folder
from girder.exceptions import RestException

from .util import (
    DANDISET_IDENTIFIER_COUNTER,
    DANDISET_IDENTIFIER_LENGTH,
    get_or_create_drafts_collection,
    validate_dandiset_identifier,
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

        new_identifier_count = Setting().collection.find_one_and_update(
            {"key": DANDISET_IDENTIFIER_COUNTER},
            {"$inc": {"value": 1}},
            projection={"value": True},
        )["value"]
        padded_identifier = f"{new_identifier_count:0{DANDISET_IDENTIFIER_LENGTH}d}"

        meta = {
            "name": name,
            "description": description,
            "identifier": padded_identifier,
            "version": "draft",
        }

        drafts = get_or_create_drafts_collection()
        folder = Folder().createFolder(
            drafts,
            padded_identifier,
            parentType="collection",
            creator=self.getCurrentUser(),
        )
        folder = Folder().setMetadata(folder, {"dandiset": meta})
        return folder

    @access.public
    @describeRoute(
        Description("Get Dandiset")
        .param("identifier", "Dandiset Identifier")
        .param(
            "version", 'Version of the Dandiset, currently only "draft" is supported.'
        )
    )
    def get_dandiset(self, params):
        if "identifier" not in params or "version" not in params:
            raise RestException("identifier and version required.")

        identifier, version = params["identifier"], params["version"]

        if not identifier or not version:
            raise RestException("identifier and version must not be empty.")

        if not validate_dandiset_identifier(identifier):
            raise RestException("Invalid Dandiset Identifier")
        if version not in ["draft"]:
            raise RestException('Invalid Dandiset Version, must be one of ["draft"]')

        # Ensure we are only looking for drafts collection child folders.
        drafts = get_or_create_drafts_collection()
        doc = Folder().findOne(
            {
                "parentId": drafts["_id"],
                "meta.dandiset.identifier": identifier,
                "meta.dandiset.version": version,
            }
        )
        if not doc:
             raise RestException('No such dandiset found.')
        return doc
