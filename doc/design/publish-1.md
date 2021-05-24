# Moving Parts

This is a summary of system components that are relevant to publish and how they relate to each other.

### Dandiset
A DANDI dataset.
Each dandiset is guaranteed to have a draft Version, and can also have any number of published Versions.

### Version
Versions consist of a JSON blob of Dandiset metadata and any number of Assets.
There are two kinds of Version: draft and published.
Published Versions are immutable, only draft Versions are editable (except admins, who have superpowers).
Versions also track the validation status of their Dandiset metadata. Asset metadata validation is not recorded in the Version.

The metadata that is stored in the DB is strictly the user-specified metadata.
Computed metadata, like `assetsSummary`, `size`, etc. are injected when the metadata is requested through the API.
Published Versions also record some information about the publishing process (dates, current API version, doi, etc.)
This information is used to generate the `publishedBy` and other publish-specific fields, which are likewise injected.

### AssetBlob
This is basically just a pointer to a blob in `blobs/` on S3.
AssetBlobs are central to how we implement deduplication of blobs in S3.
Multiple Assets can refer to the same AssetBlob, meaning we only need to store each blob in S3 once.
Each Asset could have a different metadata record for the same AssetBlob.

Whenever a new AssetBlob is created, a background task runs to compute the sha256 checksum (a "digest") of the blob.
This can take a long time for large blobs, as it must stream all of the data from S3.
This checksum is stored on the AssetBlob, not in the Asset metadata.

### Asset
Assets consist of a JSON blob of Asset metadata and a reference to an AssetBlob.
Versions and Assets are many-to-many; a Version can have any number of Assets, and an Asset can belong to any number of Versions (even, hypothetically, versions in different Dandisets).
Assets also track their validation status.

Uploading new data or modifying the metadata of an Asset doesn't actually modify the Asset.
Instead, it creates a new Asset and replaces the reference to that Asset in the Version.
This ensures that other Versions which might refer to the original Asset are unmodified, while the Version containing the Asset being modified reflects the changes correctly.

When Asset metadata is requested through the API, some extra information is injected.
* `size`, `path` are both properties of the AssetBlob, so these are injected.
* `contentUrl` is dependent on which version the Version the asset belongs to, so it must be injected.
* If the AssetBlob digest has finished calculating, it is injected into the `digests` field of the metadata.
* The oldest published Version that the Asset belongs to is queried, and the `publishBy` and `datePublished` fields for that Version are injected into the Asset metadata.
If an asset does not belong to any published Versions, `publishedBy` is not injected.

Because "modifying" an Asset actually creates a new Asset, Asset metadata will largely be stable despite having dynamically computed fields.
`digests` will change when the digest is calculated, but everything else is immutable.

### Metadata Schemas
Version metadata and Asset metadata must conform to defined schemas.
There are two sets of schemas.
The first applies to both draft and published metadata, and is used by the web metadata editor.
The second is more restrictive, and only applies to published metadata.
It requires additional fields like `datePublished`, `publishedBy`, and `doi` that are only knowable at publish time.
The second one is used to validate metadata prior to publish.

The JSON schemas can be found at https://github.com/dandi/schema.

The pydantic models can be found and imported from https://github.com/dandi/dandischema.
dandi-api will look up the JSON schema for the specified `schemaVersion` and use it for validation. Hopefully at some point we can find a way to provide arbitrary pydantic model versions and use those instead.

# Validation process
Whenever metadata is modified, a validation task runs in the background to ensure that everything is ready for publish.
There are separate tasks for version metadata validation and asset metadata validation which use different schemas.

The validation tasks work by preparing the metadata as if to publish the Version or Asset, then checking if that new metadata conforms to the publish schema.

Note that the asset metadata validation task actually requires both a Version and an Asset, since the `contentUrl` field of the Asset is different depending on which Version the Asset belongs to.

Versions can have the following validation states:
* `PENDING`
* `VALIDATING`
* `VALID`
* `INVALID`
* `PUBLISHED` (note that assets do not have this)

The `PUBLISHED` state means that Versions are technically not `VALID` after they are published, so they cannot be publish repeatedly without changes.
The next time a change is made to the metadata, the validation task will run on the version, which will change the state to `VALID`/`INVALID`, re-enabling publish.

Assets can have the following validation states:
* `PENDING`
* `VALIDATING`
* `VALID`
* `INVALID`

Because validation works with already computed metadata that is presumable of limited size, it is a very fast running task.

# Publish
Publishing a draft Version creates a new published Version that is a complete copy of the draft Version, but is immutable and permanent.

Publish is started through an API call, presumably made by a user clicking the `Publish` button in the web GUI.
Only dandiset owners have permission to use the API endpoint.
* During development, only admins can publish.

If a Version is not `VALID` or any of the Assets in the Version is not `VALID`, publish is not allowed.

## Publish process
1. The dandiset is locked so that no other publishes can happen simultaneously.

2. A new published Version is created with the required publish metadata information.
It is initialy empty.

3. A new DOI is created that points to the new Version.
This is an API call to an external service, https://datacite.org/.
This involves digesting the Version metadata into something that can be used by Datacite.
See the doi-generation-1.md design document for more details.

4. For every draft Asset in the draft Version, the required publish metadata fields are injected, turning those Assets into published Assets.
Published Assets, e.g. Asssets that already have those fields from previous publishes, _are skipped_.
Because they describe Assets that have already been published in a past version, there is no reason to re-publish them.

5. Associate all of the publish Assets, new and old, with the new published Version.

6. The dandiset is unlocked.

7. An email is sent to the owners that the Dandiset is published.

8. Asynchronously, manifest files (`dandiset.yaml` and `assets.yaml`) are written out to S3 describing the newly published Version by a background task.

Say that a user publishes a Dandiset for the first time, modifies a single Asset, then publishes again.
During the first publish, all of the Assets will be drafts, so they will all be promoted to published Assets via metadata injection.
Modifying the published Asset will create a new draft Asset, so the Dandiset will have a single draft Asset and all other Assets published.
During the second publish, the publish process will also "publishify" the draft Asset, but leave the formerly published Assets alone.

The end result is that the second published Version contains one Asset that was published at the same time as the Version, and many Assets that were published in the first published Version.
The draft Version will point to the same Assets as the second published Version.

## Publish process performance
The first time a Dandiset is published, all of the Assets need to be published, which is a potentially intensive DB request.
Because the entire publish process happens in an API call, this may degrade performance for Dandisets with very large numbers of Assets.
We may eventually need to break the logic of the publish process into a background task which is dispatched by the API call.
The API call would still lock the Dandiset to prevent multiple publishes, and to indicate to users that the publish is in progress.
