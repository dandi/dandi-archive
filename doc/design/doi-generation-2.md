# DOI for Draft Dandisets

Author: Yaroslav O. Halchenko & Dorota Jarecka

## The current approach

- [initial design doc](./doi-generation-1.md)
- overall:
   - inject fake DOI upon dandiset creation
   - mint proper DOI only upon dandiset publication (function `create_doi`)

### Issues with the Existing Approach

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

- Instead of a fake DOI, upon creation of a **public** dandiset, mint and use a legit `Draft DOI` `10.48324/dandi.{dandiset.id}` with
  - *minimal metadata* entered during creation request (title, description, license)
  - DLP URL `https://dandiarchive.org/dandiset/{dandiset.id}`
  - For embargoed dandiset, **do not** specify any metadata besides the DLP URL.
  - If minting a DOI fails, we need to raise exception to inform developers about the issue but proceed with the creation of the dandiset.
- Upon changes to dandiset metadata record (so, of a draft version of dandiset), for public (non-embargoed dandisets):
  - For `Draft DOI` (dandiset was not published yet): try to update/make it `Findable`.
    - If fails - keep Draft since there is no validation, try to update datacite metadata record while keeping the same target URL.
    - **Question to clear up**: what happens to Draft DOI if metadata record is invalid? It seems to create one with no metadata, but does it update only the fields it knows about?
  - For `Findable DOI` 
    - if it is still a draft version but which had legit metadata, we try to update metadata. If fails, we either ignore or just add a comment somewhere that "record might not reflect the most recent changes to draft version".
      - I think we need to add to validation procedures, validation against datacite metadata record, and reporting errors to the user so that users address them before trying to publish. May be we should validate only if no other errors (our schema validation) were detected to reduce noise, or just give a summary that "Metadata is not satisfying datacite model, fix known metadata errors first."
    - if dandiset was published at least once (has version) -- we do not update anything since DLP points to that published version.
  - **TODO: figure out how to annotate Draft version, so it always says that it is a draft version and thus potentially not used for citation if that could be avoided**
- Upon changes to dandiset metadata record, for embargoed dandisets don't do anything.
- Upon unembargoing dandiset: update `Draft DOI` metadata record with current metadata **after** unembargoing.
- Upon publication of the dandiset:
  - (already done currently) mint a proper `Findable` version DOI `10.48324/dandi.{dandiset.id}/{version}`
  - update Dandiset-wide DOI (`Draft` or `Findable`) `10.48324/dandi.{dandiset.id}` with metadata provided for the version DOI, while keeping URL pointing to DLP instead of the released version.
    - if Dandiset-wide DOI was in `Draft` state, it would be updated to `Findable` state (should work since we know metadata record passed validation).
       - **Question to clear up**:how to do that in API
    - **Question to clear up**: behavior on what happens if metadata record is invalid?

## Concerns to keep in mind/address

- Draft dandiset might not have sufficient metadata to mint a proper DOI, or metadata might not be "proper" (fail validation) thus causing issues with minting a DOI
  - **Solution**: start with Draft (not findable) DOI, and then upon publication mint a "findable" DOI.
  - **Follow up concern**: after dandiset and DOI publish, metadata of the Draft version of the dandiset could still be changed.
    This potentially making changed record again "invalid".
    Should be Ok'ish
- Test site of datacite had different result of validation that the primary one

- `Draft` DOI is not visible/usable by users. We might want to switch it to `Findable` as soon ASAP (when datacite validates record ok).
- `Findable` DOI cannot be deleted, but in principle we allow for deletion of dandisets.
  - We might want a dedicated 404 page for deleted dandisets, or at least a message that the dandiset was deleted, and ideally describe the reason why it was deleted ("Upon request of maintainer", "Due to violation of terms of service", etc.)
  - Then we adjust DOI record to point to that page.

- Should we do anything at dandischema level?
  - yes, `to_datacite` and potentially model might need to change to accomodate for needed changes.

- Should we do anything at DLP level?

- Should we somehow reflect interactions with DataCite in Audit log?


# Targets TODO before implementation

- develop a script, which tests on test fabric of datacite changes as introduced to all dandisets in the archive by
  - for each dandiset
    - generate a record for overall *dandiset DOI* corresponding to metadata of the first release if any exists, otherwise corresponding to metadata of the draft version
    - for each release: mint a new *version DOI* for that release + possibly update *dandiset DOI* to correspond to potential changes in metadata
    - update *dandiset DOI*  to metadata of draft version

