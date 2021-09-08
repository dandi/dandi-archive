# Embargo support

## User experience

### uploading embargoed data
When a user creates a dandiset, they have the option to mark it as "open" or "embargoed". There is some help text that explains these options, either as a hover-hint or some other way. The text for "open" would indicate that the dandiset would be visible to anyone.

If "embargoed" is selected, a page would be displayed that would explain the rules of embargoed data. The user is required to check "I agree" before proceeding. There is also a "back" option. On this page, the user is required to enter the grant or award number, and we would ideally validate that this is an active award. The message would indicate that this option is only available to BRAIN Initiative grants, and that the landing page of the dandiset would be visible to everyone but the underlying assets would not be. As per recent NIH policy, the user will be required to make the dandiset "open" upon the first publication of the data, or when the funding for the grant runs out, whichever comes first. We will be able to determine when the grant expires and we will automatically open the dandiset if it has not already been opened. Using the grant number, we determine the embargoedUntil date and add it automatically as metadata which is visible publicly on the dandiset landing page.

It is expected that each grant have at least one of these embargoed dandisets. Since it is not always clear from the outset how the data from a grant will be divided into publications, it is expected that several groups may start with a single dandiset.

For embargoed data the owner would have options to add user permissions, with an interface similar to Google Docs:

* add read-only member. This would be used for collaborators with team members who do not need to submit data but only to read it. This would also be useful for reviewers of manuscripts who need to see the data as part of the review process. Read access allows a user to view available assets, and download them with the web API, the Python API, and reading data directly using s3 streaming. A DANDI Hub user will automatically use the credentials from the dandi hub account they are currently using.
* add owner. This would give them read and write permissions and the ability to add users, including owners.

Permissions are all by dandiset, not by asset. If a user needs to set different permissions for specific assets within the dandiset, they will need to create a new dandiset and put the assets in this separate place.
When a there is a new publication, the user is expected to create a new dandiset for this publication. There should be an online interface for copying assets from an existing dandiset to this one.

### requesting access

When a user without access to an embargoed dandiset visits the landing page, they see a message that says that this
dataset is currently under embargo until the embargo end date. They have a button to request read access. If they
click this button, an email is sent to the contact person with a link that leads them to an interface where they can
give this user access.

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
