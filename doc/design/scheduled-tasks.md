# Asynchronous Tasks
We are currently (7/16/2021) using celery to run these asynchronous tasks:

 * Calculating blob sha256 digests
 * Writing dandiset.yaml and assets.yaml after publishing
 * Validating asset metadata
 * Validating dandiset metadata

These all work well at the usage levels that we are currently seeing, but may not scale well into the future.
Specifically, every time an asset is uploaded, asset metadata and dandiset metadata are re-validated.
When uploading large batches of assets, dandiset metadata is validated repeatedly and unnecessarily.

## Motivation
Currently (7/16/2021), every time a Version is saved, it recalculates the value of the `assetsSummary` metadata field.
This requires performing a `SELECT *` on all Assets in the Version, which does not scale well for Versions with lots of Assets.
Because uploading a new Asset to a Version involves saving that Version, uploading lots of new assets will eventually start causing request timeouts as the number of Assets increases.

We would like to move this `assetsSummary` calculation into a celery task, but we also don't want to trigger a separate task for every new Asset, as that would only delay the load on the DB.
We need a way to run this task only once per batch of uploads.

## Proposal
Instead of adding a new task to the queue whenever something needs to be done, we use a scheduled job that runs the task only when necessary.

Since `assetsSummary` calculation and dandiset metadata validation both need to be triggered in the same circumstances, we'll consider them together.

#### Request thread
Whenever a Version is modified, a flag is set on the Version indicating that it has been modified (instead of queueing a task as it does now):
```
  # Things that modify the version, necessitating a validation/assetsSummary computation
  ...
  # validate_version_metadata.delay(version.id)
  version.status = status.MODIFIED
```

#### Scheduled job
Separately, a scheduled job that runs on a configurable fairly tight interval will check for any Versions that need to be updated.
For each of those Versions, it also checks that the Version hasn't been modified in a certain amount of time. This prevents DB locks from happening while Assets are still being uploaded to the Version.

The code would look something like this:
```
def scheduled_task():
  versions = Version.objects.filter(status=status.MODIFIED).filter(modified__lt=timezone.now() - 5 minutes)
  # SELECT ... FROM api_version WHERE api_version.status = "MODIFIED" AND now() - api_version.modified > 5 minutes;
```

For each of those Versions, the job would then calculate `assetsSummary`, inject it into the metadata, and perform the validation, marking the Version accordingly.

## Changes to existing tasks
We shouldn't need to change how calculating blob sha256 digests or how writing dandiset.yaml and assets.yaml work at all.
They don't block the DB in any meaningful way, and so can continue working as they always have.

Validating asset metadata could possibly be run with a job, but I would recommend not switching it yet.
Uploading or updating Assets doesn't happen with the same frequency as with Versions, so it doesn't benefit from debouncing in the same way.

Validating dandiset metadata will, as described, be a dispatched by the scheduled job, and will also calculate `assetsSummary` before validating.
