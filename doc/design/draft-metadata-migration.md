Premise: Draft metadata should always be in the latest schema version.

There are a few places in the API where draft metadata are altered (POST, PUT) and served (GET). Note that the UI and 
API use a shared schema version. All actions should thus assume that this is the only version available to the UI and
server. Any other versions need to be migrated to this version for any display or editing.

1. The API should call dandischema `migrate` on all metadata exchanges of draft metadata.
2. The API can have the option (parameter `?migrate=true`) of providing migration on a `GET` on published metadata. 
   This would be needed for the UI to display landing pages for published dandisets with older schemas.
3. To determine the state of validity, the API should also revalidate all draft metadata on any schema version change 
   in the infrastructure.


