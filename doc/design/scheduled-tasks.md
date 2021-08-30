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
Instead of adding a new task to the queue to calculate `assetsSummary`, we use a scheduled job that runs the task only when necessary.

Since `assetsSummary` only needs to be recalculated when an asset is added, removed, or modified, we don't want it to recompute whenever the Version is modified, as it is now.

#### Request thread
Whenever an asset is added (`POST`), removed (`DELETE`), or modified (`PUT`), a flag `needs_recomputing` is set on the Version indicating that it needs to be recomputed (instead of queueing a task as it does now):
```
  # validate_version_metadata.delay(version.id)
  version.needs_recomputing = True
```

#### Scheduled job
Separately, a scheduled job that runs on a configurable fairly tight interval will check for any Versions that need to be updated.

The full code would look something like this:
```
def scheduled_task():
  with transaction.atomic():
    versions = Version.objects.filter(needs_recomputing=True).filter(modified__lt=timezone.now() - 5 minutes)
    # SELECT ... FROM api_version WHERE api_version.needs_recomputing AND now() - api_version.modified > 5 minutes;

    for version in versions:
      try:
        # Calculate assetsSummary
        version.metadata['assetsSummary'] = calculate_assetsSummary(version)

        version.needs_recomputing = False

        # The version has been modified, so it needs to be revalidated
        version.status = PENDING
        version.save()

        # Dispatch the version validation task
        validate_version_task.delay(version.id)
      except:
        # Something went wrong, mark the version as dirty again so it can be retried next task
        version.needs_recomputing = True
        version.save()
```

The entire task happens within a [Django transaction](https://docs.djangoproject.com/en/3.2/topics/db/transactions/#controlling-transactions-explicitly), so we don't have to worry about requests making concurrent modifications.
This is a little overzealous because if there are multiple versions to update, they will all be locked until they have all finished computing.
In practice it is very unlikely that two or more users will coincidentally finish making modifications at the same time.

For Version that `needs_recomputing`, the query checks that the Version hasn't been modified in a certain amount of time (say 5 minutes). This prevents DB locks from happening while Assets are still being uploaded to the Version.

The actual task logic would be applied to each version: calculate `assetsSummary`, inject it into the metadata, marking the version as no longer needing recomputing, and dispatching a follow-up task to validate the version.

Recomputation should fail very infrequently, either because of SQL errors or because of introduced bugs in our code.
In the event of an error, `needs_recomputing` should be set to `True` so that it is retried, hopefully resolving intermittent errors.
The error should then be thrown so that it shows up in Sentry.

## Related changes
No other tasks would benefit from this same debouncing, so all our other tasks will remain the same.

The only other required change is to make Versions with `needs_recomputing == True` report as non-valid for publishing purposes.
If a version needs to be recomputed, it is not eligible for publishing.

We will need two configurable settings:
* The interval that the scheduled task runs at.
* How long the scheduled task should wait after a Version is modified before recomputing `assetsSummary`.

Integration tests will be able to set these configuration values to something like 1 second each, so the task finishes in a timely manner.
