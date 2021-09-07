# Embargo support

## Principles

### Use of key stores

Rely on the fact that "stores" (`blobs/`, and future `zarr/` see #295) although "public" are not pragmatically "usable" for users, since the assets named based on their IDs, and provide no semantic meaning (not even a file extension).
It would be an expensive procedure for someone to "mine" the store(s) for some relevant data they would like to "steal".

### "Move" operation within/between buckets is "expensive"

There is no AWS S3 API for quick move (renaming) of a key within a bucket.
As a result, "move" operation can be **very** expensive in terms of traffic (thus possibly cost if not "sponsored"), time it would take for transfer, implementation e.g. handling of possible errors during transfer, etc

### Publishing a dandiset is enabled only for Open dandisets

### Use-cases to fulfill

- UC-Collaboration: authorized users of emabrgoed dataset should be able to manipulate it as easily as if it was a public dataset.
- UC-Review: ability to make embargoed dataset available to other users "read-only".
- UC-Promotion (findability): make embargoed dataset discoverable by others, so that Corresponding contact could be contacted to provide access to the dandiset.

UC-Promotion is somewhat optional, this design proposal aims to un-conditional (i.e. no option to configure for it) support, but it could truly be made optional.

## Implementation

### Asset store(s) (`blobs/`)

- No changes required per se
- Optional: remove `s3:ListBucketVersions` and `s3:ListBucket` for the keystores prefixes. Rationale:
    - it would totally prevent the unlikely, but possible, access to embargoed data through full navigation of the keystores
    - it would not hinder accessibility to public (not embargoed) data since key stores are not usable *as is* anyways, access to specific keys goes through API or exported manifest files

### `dandischema`

- ??? move `access: List[AccessRequirements]` from `CommonModel` level to `Dandiset`, so to not requiring mutating or minting new `Asset`s records upon updating Dandisets from `embargoed` to `public`

### Types of access

- `open` - fully `open` from the start
- `embargoed` - eventually auto-updates to `open` upon reaching `embargoedUntil` in `AccessRequirements`

TODO: ATM [dandischema](https://github.com/dandi/dandischema/blob/master/dandischema/model_types.py) defines AccessTypes: `Open`, `Embargoed`, `Restricted`.  I am not including `Restricted` (embargoed without temporal or publish restrictions?) aside.

### dandi-api

#### Dandiset

- Create (`POST /dandisets/`) endpoint gains optional
  - `accessType` field to enter, defaulting to `open`
  - `embargoedUntil` field to be specified, only if `accessType == 'embargoed'` and error out if specified for `open`
- DB for dandiset gains `accessType` column to avoid lookup in metadata
- `PUT /dandisets/{dandiset__pk}/versions/draft/`, if accessType is changed from known
  - ERROR out if change from `open` to `embargoed`
  - if change into `open`:
    - update DB's `accessType` for dandiset to `open`
- all endpoints under `/dandisets/{versions__dandiset__pk}/versions/{versions__version}/assets/` for an embargoed dandiset require user to be listed in `GET /dandisets/{dandiset__pk}/users/` and otherwise
  - if session is not authenticated: 401 (with appropriate WWW-Authenticate etc dance to get user logged in?)
  - if session is authenticated: 403
- export of assets manifests to S3 is disabled for `embargoed` dandisets

#### Users

- ... TODO: read-only type of user association with a dandiset

#### Publishing (Making a versioned release)

- Publishing should be restricted to `open` datasets

#### Considerations

- A made `opn` dandiset cannot be (re-)`embargoed`

### web-ui

- Create:
  - expose the selector for AccessType
  - if Embargoed is chosen, expose UI to optionally provide `embargoedUntil` to specify the date when dandiset becomes public
- `accessType` editing in meditor allow for change from `Embargoed` to `Open`

### dandi-cli

- no changes


### DataLad dandisets (https://github.com/dandisets/)

- embargoed dandisets are made "Private" on github
-

## Relevant prior issues/discussions

- Roadmap issue: https://github.com/dandi/helpdesk/issues/12
- Idea for encryption at HDF5 level: https://github.com/dandi/dandi-infrastructure/issues/16
- Prior dump of ideas: https://github.com/dandi/dandi-api/issues/158
