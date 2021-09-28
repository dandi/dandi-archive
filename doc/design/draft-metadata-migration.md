Premise: Draft metadata should always be in the latest schema version.

There are a few places in the API where draft metadata are altered (POST, PUT) and served (GET). Note that the UI and
API use a shared schema version. All actions should thus assume that this is the only version available to the UI and
server. Any other versions need to be migrated to this version for any display or editing.

This proposal only applies to the `schemaVersion` of dandiset metadata, not asset metadata.

1. The API should provide `GET /dandisets/{dandiset_pk}/versions/{version}/migrated/` endpoint, which would return the metadata of the version after migrating it to the current schemaVersion, and a description of changes and warnings.
   For up to date metadata, this is obviously a no-op.
   The meditor would use this endpoint to fetch the draft metadata whenever it is opened, which ensures that editing a draft with out of date schema version will implicitly migrate it.
   This endpoint can also be used to get the metadata of published versions as if they were migrated.
2. The API will not accept metadata with out of date `schemaVersion`.
   Draft metadata with out of date `schemaVersion` is considered invalid by the API (even if it would pass validation) and is not publishable.
3. To determine the state of validity, the API should also migrate and revalidate all draft metadata on any schema version change
   in the infrastructure.
   This can be a manual maintenance task that is always done after making changes to the schema.
4. Publish should not be enabled for any dandisets with a metadata schemaVersion that is not up to date.

When the schemaVersion is incremented, we will do our best to migrate all draft metadata accordingly, so that users never even notice.
In the event that a schema change requires user intervention (i.e. adding a new required field that we cannot infer):

1. When the schemaVersion is incremented, all drafts are revalidated.
   This marks any unmigrateable drafts as invalid, and thus unpublishable.
2. The owner will eventually need to publish their draft, which is not permitted because it is invalid.
3. The owner is prompted to open the meditor.
   The meditor uses the `.../migrated/` endpoint to provide the best possible approximation of the required metadata.
4. The owner reviews the content in the meditor, makes the required changes to resolve the validation errors, and saves.
5. The draft is validated and is now publishable.
