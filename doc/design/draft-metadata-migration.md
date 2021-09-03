Premise: Draft metadata should always be in the latest schema version.

There are a few places in the API where draft metadata are altered (POST, PUT) and served (GET). Note that the UI and 
API use a shared schema version. All actions should thus assume that this is the only version available to the UI and
server. Any other versions need to be migrated to this version for any display or editing.

This proposal only applies to the `schemaVersion` of dandiset metadata, not asset metadata.

1. The API should provide `GET /dandisets/{dandiset_pk}/versions/{version}/migrated/` endpoint, which would return the migrated metadata of the version, and a description of changes and warnings.
   For up to date metadata, this is obviously a no-op.
   The meditor would use this endpoint to fetch the draft metadata whenever it is opened, which ensures that editing a draft with out of date schema version will implicitly migrate it.
   This endpoint can also be used to get the metadata of published versions as if they were migrated.
2. The API will not accept metadata with out of date `schemaVersion`.
   Draft metadata with out of date `schemaVersion` is considered invalid by the API (even if it would pass validation) and is not publishable.
2. The API can have the option (parameter `?migrate=true`) of providing migration on a `GET` on published metadata. 
   This would be needed for the UI to display landing pages for published dandisets with older schemas.
3. To determine the state of validity, the API should also migrate and  revalidate all draft metadata on any schema version change 
   in the infrastructure.
4. Publish should not be enabled for any dandisets with a metadata schemaVersion that is not up to date.


