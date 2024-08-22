# DOI for Draft Dandisets

Author: Yaroslav O. Halchenko & Dorota Jarecka

The current approach:

- [initial design doc](./doi-generation-1.md)
- overall:
   - inject fake DOI upon dandiset creation
   - mint proper DOI only upon dandiset publication

## Issues with the Existing Approach

- [Stop injecting "fake" DOIs into draft dandisets](https://github.com/dandi/dandi-archive/issues/1709)
- [Unpublished Dandisets display a DOI under `Cite As`](https://github.com/dandi/dandi-archive/issues/1932)

## Proposed Solution

Initially proposed/discussed in

- [Create and maintain a "Findable" DOI for the Dandiset as a whole](https://github.com/dandi/dandi-archive/issues/1319)

and boils down to the adoption of approach of Zenodo of having a DOI which always points to the latest version of the record.

DataCite allows for three types of DOIs ([DataCite](https://support.datacite.org/docs/what-does-the-state-of-the-doi-mean)):

- `Draft`. We do not use those.
  *Can be deleted, and they require only the identifier itself in order to be created or saved. They can be updated to either Registered or Findable DOIs. Registered and Findable DOIs may not be returned to the Draft state, which means that changing the state of a Draft is final.*
- `Registered`. Like `Findable` but not indexed for search, so we do not use them.
- `Findable`. Is the type we use for published dandisets.
  Requires to be valid (pass validation to fit the datacite schema) to be created.

We propose to:

- Instead of a fake DOI, upon creation of dandiset, mint and use a legit `Draft` DOI `10.48324/dandi.{dandiset.id}` with
 - metadata entered during creation request (title, description, license)
 - DLP URL `https://dandiarchive.org/dandiset/{dandiset.id}`
 - For embargoed dandiset, **do not** specify any metadata besides the DLP URL.
- Upon changes to dandiset metadata record, for public (non-embargoed dandisets), try to update datacite metadata record while keeping the same target URL.
  - For Draft DOI (dandiset was not published yet), there is no validation.
    - **Question to clear up**: what happens to Draft DOI if metadata record is invalid? Does it fail to update altogether? does it update only the fields it knows about?
  - For Findable DOI (dandiset was published), metadata record must pass validation, so we might fail to update.
    But that should be ok.
- Upon unembargoing dandiset: update (Draft) DOI metadata record with current metadata.
- Upon publication of the dandiset:
  - (already done currently) mint a proper `Findable` version DOI `10.48324/dandi.{dandiset.id}/{version}`
  - update Dandiset-wide DOI `10.48324/dandi.{dandiset.id}` with metadata provided for version DOI, while keeping URL pointing to DLP instead of the released version.
    - if Dandiset-wide DOI was in Draft state, it would be updated to Findable state (should work since we know metadata record passed validation).

## Concerns to keep in mind/address

- Draft dandiset might not have sufficient metadata to mint a proper DOI, or metadata might not be "proper" (fail validation) thus causing issues with minting a DOI
  - Solution: start with Draft (not findable) DOI, and then upon publication mint a "findable" DOI
  - **Follow up concern**: after dandiset and DOI publish, metadata of the Draft version of the dandiset could still be changed.
    This potentially making changed record again "invalid".then when people change metadata
- test site of datacite had different result of validation that the primary one

- `Findable` DOI cannot be deleted, but in principle we allow for deletion of dandisets.
  - We might want a dedicated 404 page for deleted dandisets, or at least a message that the dandiset was deleted, and ideally describe the reason why it was deleted ("Upon request of maintainer", "Due to violation of terms of service", etc.)
  - Then we adjust DOI record to point to that page.

- Should we do anything at dandischema level?

- Should we do anything at DLP level?

- Should we somehow reflect interactions with DataCite in Audit log?
