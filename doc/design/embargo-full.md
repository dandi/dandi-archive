# Embargo
This document takes the Embargo MVP as a predicate and describes the remaining features required for full Embargo support.

## Non-private embargoed dandisets

In the MVP, all embargoed dandisets are invisible to non-owners.
There should be an additional embargo mode, "Visible".
Visible embargoed dandisets are searchable, viewable, and their metadata is public to everyone, but their asset data and metadata is not.

Users will select their desired embargo mode using radio buttons when creating a dandiset.

In addition to the dandiset `embargo_status` values from the MVP (`PRIVATE`, `RELEASING`, and `PUBLIC`), there is a new value, `VISIBLE`.
All of the dandiset and version endpoints will only hide `PRIVATE` dandisets from appearing.
The asset endpoints will not permitted for anonymous users on embargoed assets that are `PRIVATE` or `VISIBLE`.

### TODO: can users switch the embargo mode between private and visible?
It would be easy to do, since it's just a change `embargo_status`, no data needs to be copied.
We would need a place in the UI to set that.
