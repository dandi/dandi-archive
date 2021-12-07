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


## Read-only access
In the MVP, the only role a user can have on a dandiset is "Owner".
There should be a new role, "Reviewer".

Reviewers are allowed to access asset data on private and visible embargoed dandisets.
Reviewers are allowed to see private embargoed dandisets.
Reviewers are not allowed to make any changes to embargoed dandisets.

If a user is a reviewer on an embargoed dandiset, they do not have any permissions on other embargoed dandisets unless explicitly added to those dandisets as well.

The web UI will show reviewer selection directly under owner selection.

Reviewers are not acknowledged for unembargoed dandisets and will not show up in the web UI.

This will be implemented as a new django-guardian role.
All read endpoints for assets are permitted for users who are reviewers of the embargoed dandiset.
All read endpoints for dandisets and versions will treat reviewers the same as owners.
All write and upload endpoints are unchanged.