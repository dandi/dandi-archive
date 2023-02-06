# Embargo
This document takes the Embargo MVP as a predicate and describes the remaining features required for full Embargo support.

## Non-private embargoed dandisets
In the MVP, all embargoed dandisets are invisible to non-owners.
There should be an additional embargo mode, "Restricted".
Restricted embargoed dandisets are searchable, viewable, and their metadata is public to everyone, but their asset data and metadata is not.

Users will select their desired embargo mode using radio buttons when creating a dandiset.

In addition to the dandiset `embargo_status` values from the MVP (`EMBARGOED`, `UNEMBARGOING`, and `OPEN`), there is a new value, `RESTRICTED`.
All of the dandiset and version endpoints will only hide `EMBARGOED` dandisets from appearing.
The asset endpoints will not permitted for anonymous users on embargoed assets that are `EMBARGOED` or `RESTRICTED`.

### TODO: can users switch the embargo mode between embargoed and restricted?
It would be easy to do, since it's just a change `embargo_status`, no data needs to be copied.
We would need a place in the UI to set that.


## Read-only access
In the MVP, the only role a user can have on a dandiset is "Owner".
There should be a new role, "Reviewer".

Reviewers are allowed to access asset data on private and restricted embargoed dandisets.
Reviewers are allowed to see private embargoed dandisets.
Reviewers are not allowed to make any changes to embargoed dandisets.

If a user is a reviewer on an embargoed dandiset, they do not have any permissions on other embargoed dandisets unless explicitly added to those dandisets as well.

The web UI will show reviewer selection directly under owner selection.

Reviewers are not acknowledged for unembargoed dandisets and will not show up in the web UI.

This will be implemented as a new django-guardian role.
All read endpoints for assets are permitted for users who are reviewers of the embargoed dandiset.
All read endpoints for dandisets and versions will treat reviewers the same as owners.
All write and upload endpoints are unchanged.

## Anonymous read-only access
Embargoed dandisets need to be shared anonymously with reviewers.
There are two modes to support: browsing the embargoed dandiset anonymously, and downloading the asset data anonymously with the CLI.

Browsing the embargoed dandiset anonymously can be achieved with a secret URL parameter unique to the dandiset.
When the web UI detects the secret URL parameter, it passes it as an authorization token header/URL parameter to all API requests.
The API will treat any request with the correct secret as coming from a reviewer, unless the user is already an owner.

A link to the dandiset with this secret URL parameter is included somewhere on the embargoed dandiset page as a way to share access anonymously.

### TODO implementation details
### TODO how to download anonymously with the CLI?

## Embargo period enforcement
NIH embargoes (and embargoes in general) will have an end date to ensure that the data is not secret forever.
We will enforce that an end date be specified for every new embargoed dandiset, and forcibly release embargoed dandisets that expire.

The MVP collects the NIH award number and stores it in the metadata.
We can use the NIH API to determine the required release date for the award (?).
### TODO should we gather the end date during creation time, as we do award number?

We should add scheduled jobs (in the manner of garbage collection) that:
* Notify admins and owners of any embargoed dandisets without end dates
* Notify admins and owners of any embargoed dandisets that are approaching their end dates (daily emails for the last week?)
* Notify admins and owners of any embargoed dandisets that have past their end dates

Admins will be at liberty to manually delete or unembargo embargoed dandisets without end dates.
Admins will be at liberty to manually unembargo embargoed dandisets that have expired.

### TODO policy details


## Zarr download
The MVP embargo zarr download design involves a request to our API server for every file being downloaded from the zarr archive.
Since zarr archives can contain hundreds of thousands of files, there would be a corresponding number of requests, which might degrade performance of the API server.
If this becomes an issue, we could:
* Spin off the zarr download functionality into a separate microservice that can be scaled separately, and would isolate any accidental DDOS effects.
  This could be as simple as adding a new django app and a new Heroku dyno, or as complex as a Lambda@Edge+CloudFront service.
* Dynamically provision IAM users with permission to access prefixes in the embargo bucket and distribute access keys to users.
  This would require the API server to manage IAM directly, which is a lot of complexity to manage.
* Make the embargo bucket publicly readable, but not listable.
  If anyone knows the full S3 object key they have the ability to download the data, but they will not have the ability to search for or scan the bucket for new content.
  We would then distribute the zarr_id to anyone who needs to access an embargoed zarr archive, giving them permanent read access to it.
  The downside is that access is not revocable, since we cannot take back the zarr ID from the user or efficiently change the location of the zarr archive.

## TODO miscellaneous
- email the owners of an embargoed dandiset (and admins) when it has been successfully unembargoed
- on the stats page, display the full amount of data stored in the archive, and indicate how much of it is under embargo
  - e.g., `300 TB total data size (100 TB currently under embargo)`
  - link the word "embargo" to docs/explanation thereof