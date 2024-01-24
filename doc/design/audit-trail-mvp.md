# Audit Trail MVP

NIH has required that DANDI Archive generate audit logs while leaving undefined
what that means. We are choosing to fulfill the requirement with a feature that
indicates to Dandiset owners and admins the sequence of significant actions
taken to modify Dandisets, along with identification of who performed each
action.

The major motivation is to inform owners about how their Dandisets have changed
when a given owner did not make the change and wishes to know who to speak to
about those changes. In essence, it is a tool to support effective
collaboration.

## Requirements

1. **Persistent tracking of significant actions.** Whenever a *significant
   action* (see list [below](#significant-actions)) occurs successfully, the archive will generate a
   persistent record of that action, including the following data:
    - The date and time
    - The authorized user who triggered the action (note that this may be an actual user or the system itself for internal automated actions)
    - The ID of the Dandiset on which the action occurs
    - Event-specific data about the action itself

2. **Display of audit log (to owners and admins only).** The Dandiset landing
   page will display a rendered (i.e. human-readable) version of the log event
   data (as long as the viewing user is an owner of the Dandiset, or an admin).

   A possible example of such a display follows (the final rendered form may
   differ from this depending on best practices, etc.):
    
    ```
    YYYYMMDDTHHMMSS.mmmm: X added asset at path (/full/path) checksum
    YYYYMMDDTHHMMSS.mmmm: X updated asset at path (/full/path) checksum
    YYYYMMDDTHHMMSS.mmmm: X removed asset at path (/full/path) checksum
    YYYYMMDDTHHMMSS.mmmm: X updated dandiset metadata
    ```
    
3. **Extensible significant action list.** The significant actions the system is
   capable of tracking should be extensible--that is, in the future new actions
   should be able to be added to the system, and existing actions should be able
   to expand the specific data they carry.

## Significant Actions

The following is the list of actions performed on Dandisets that are considered
"significant" (i.e., require an audit record to be generated), along with any
additional, event-specific data each will carry with it.

|  | General data | Specific data |
| --- | --- | --- |
| Create Dandiset | date_time, user_id, dandiset_id | metadata |
| Add owner | date_time, user_id, dandiset_id | owner_id |
| Remove owner | date_time, user_id, dandiset_id | owner_id |
| Update Dandiset metadata | date_time, user_id, dandiset_id | metadata |
| Add asset | date_time, user_id, dandiset_id | asset_path, checksum, metadata, blob_id, asset_id |
| Update asset | date_time, user_id, dandiset_id | asset_path, checksum, blob_id, metadata, asset_id, old_asset_id |
| Remove asset | date_time, user_id, dandiset_id | asset_path |
| Publish Dandiset | date_time, user_id, dandiset_id | version |
| Delete Dandiset | date_time, user_id, dandiset_id | none |

## Asset chain analysis

This section provides some analysis of the historical data living in the
"`Asset` chains" kept in the `Asset.previous` links. The immediate goal is to
determine how much "significant action" data can be reconstructed therefrom;
there is also some analysis of how this may affect provenance work in the
future.

For context: because most changes to an `Asset` model cause a new model instance
to be created, and because that new `Asset` instance points to its "ancestor"
via a `previous` property, the history of an asset is at least partially
traceable through this "asset chain".

**Note: the following analysis concerns only the extent of significant action
data that is recoverable from the existing database records; it does _not_
preclude the inclusion of any significant action data _going into the future_.**

### Audit

| Action | Recoverable fields | Unrecoverable fields | Notes |
| --- | --- | --- | --- |
| Create Dandiset | date_time, dandiset_id | user_id, metadata | date_time is equal to the Dandiset’s created_at value. user_id and metadata (as they were at the beginning of the Dandiset’s lifecycle) cannot be known with certainty.<br><br> Dandisets that have already been deleted will not have any recoverable fields (though we believe it very unlikely that a Dandiset has ever actually been deleted).<br><br> Independent of asset chains. |
| Add owner | none | date_time, user_id, dandiset_id, owner_id | These events are all "summed" into the current owners list, with no way to know the evolution thereof.<br><br> Independent of asset chains. |
| Remove owner | none | date_time, user_id, dandiset_id, owner_id | These events are all "summed" into the current owners list, with no way to know the evolution thereof.<br><br> Independent of asset chains. |
| Update Dandiset metadata | none | date_time, user_id, dandiset_id, metadata | These events are all "summed" into the current Dandiset metadata, with no way to know the evolution thereof.<br><br> Independent of asset chains. |
| Add asset | date_time, dandiset_id, asset_path, checksum, metadata | user_id | The last Asset instance in the chain (i.e., the one that has a null previous pointer) represents the version of the asset that was first added to a Dandiset. Everything about this asset besides the user who uploaded it is available in the Asset instance, the AssetBlob it points to, and the association table between Dandisets and Assets that relates them.<br><br> The dandiset_id may not be recoverable for Asset instances that have been removed from a Dandiset, or for Dandisets that were deleted. |
| Update asset | date_time, dandiset_id, asset_path, checksum, metadata | user_id | As above, the user_id information is missing, and the dandiset_id may be as well. |
| Remove asset | asset_path | date_time, user_id, dandiset_id | A removed asset will be one at the head of an asset chain that has no association to a Dandiset. Unfortunately, without that association, the dandiset_id cannot be recovered, and because it is the absence of a relation that indicates removal, the date_time value is also unrecoverable. |
| Publish Dandiset | date_time, dandiset_id, version | user_id | The date_time, dandiset_id, and version are all available as part of the Version instance’s metadata. |
| Delete Dandiset | none | date_time, user_id, dandiset_id | Deleted Dandisets just don’t exist anymore, so no information (even the dandiset_id) is available. |

Note that the majority of information describing these auditable actions is
unrecoverable.

### Provenance

Provenance describes the heritage of domain artifacts in the system in terms of
how they originated and where they originated from. Many of the audit actions
described above may be thought of as simple provenance events as well: for
example, when a user publishes a Dandiset, the published `Version` that results
can be understood as originating from the draft version present in the Dandiset
at a specific time. Taken in that sense, these simple provenance events can be
identified with corresponding audit events.

More complex provenance events do not currently exist in the system. For
example, a reasonable action a user could take would be to manufacture a new
Dandiset from the state of a published version in some other Dandiset. If this
action were afforded to the user, we might think of recording a provenance event
describing the specific way in which that derived Dandiset came to be.

Because we do not currently afford such complex provenance events in the system,
the operations to fulfill the basic audit system will be sufficient to support
any provenance events in the future. See the [Operations](#operations) section below for
more details.

## Operations

In addition to providing audit-style trails for Dandisets and assets, this plan
fulfills a secondary requirement to cut the `previous` links, freeing up
non-current assets for garbage collection. As this will destroy the asset chains
from which we might draw some limited historical information, we need to
carefully design an operations plan that preserves maximal information while
empowering the garbage collection work to continue.

Because it is broadly impossible to glean all of the information needed to
reconstruct the historical audit trail for existing and deleted Dandisets, we
plan to *begin* collecting complete information with the implementation
of this design, while **preserving** a database snapshot at that
same moment so that, if we choose in the future, we may wish to reconstruct that
partial historical record. We would be essentially splitting time into two
periods: before-audit-trail (represented by the DB snapshot) and
after-audit-trail (represented by live, ongoing collection of complete audit
records).

This plan does not negatively impact future efforts at building
provenance-related features. If we need to generalize provenance events from the
audit trail, we can do so from the after-audit-trail events as needed, and the
before-audit-trail DB snapshot remains available for that purpose as well. In
essence, our plan retains the maximum possible amount of information while
freeing the system to perform new features like audit, provenance, and
comprehensive garbage collection.

In sum, this plan allows us to (1) implement audit into perpetuity sooner; (2)
preserve the available record at the moment that goes into effect; and (3)
enable the completion of garbage collection design and implementation.

The sequence of events looks like this:

1. Implement the design in this document as a pull request, but do not
   merge/release it yet (upon merge and release, the Archive will begin
   generating audit records).
2. Put the system into maintenance mode.
3. Take a DB snapshot and store it in a safe place (sponsored S3 bucket, with
   access restricted to admins).
4. Merge and release the PR.
5. Put the system into production mode.
