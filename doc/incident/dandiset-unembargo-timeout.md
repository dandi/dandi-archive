# Incident: Dandiset 002015 unembargo timed out

## Summary

Unembargoing dandiset 002015 failed on 2026-09-29 because the Celery task
that removes the `embargoed` S3 tag from every object in the dandiset
exceeded its 20-minute soft time limit. The dandiset is made up of 37 zarr
archives totalling roughly 248,000 S3 objects; tag removal touches each
object twice (`get_tags`, then `put_tags`), and even at a healthy throughput
of ~160 objects/s that takes ~26 minutes — longer than the limit allowed.
The owners received a failure notification email and the dandiset was left
in the `UNEMBARGOING` status.

## Detection

The dandiset's owners received the standard "there was an error during
unembargo" notification email and reported it. Sentry issue **DANDI-API-TK**
recorded two `SoftTimeLimitExceeded` exceptions in `unembargo_dandiset_task`
for `(dandiset_id=2015, user_id=302)`, raised on production at 19:15 and
20:09 UTC on 2026-09-29.

## Where it failed

```
unembargo_dandiset_task             dandiapi/api/tasks/__init__.py:97
 └ unembargo_dandiset                dandiapi/api/services/embargo/__init__.py:34
   └ remove_dandiset_embargo_tags    dandiapi/api/services/embargo/utils.py:65
     └ ThreadPoolExecutor.__exit__ → shutdown(wait=True) → join   ← soft limit fires here
```

`unembargo_dandiset_task` was decorated with `@shared_task(soft_time_limit=1200)`
(20 minutes). `remove_dandiset_embargo_tags` removes the `embargoed` tag from
every manifest file, every non-zarr asset blob, and — for every zarr asset —
every chunk object in the zarr, using a `ThreadPoolExecutor` capped at 4
workers (kept low deliberately, since each thread opens its own boto3 client
and memory is the binding constraint, not thread count). For a dandiset this
large, the work does not finish inside the limit.

## Root cause

The soft time limit on `unembargo_dandiset_task` (20 minutes) was sized for
the common case and did not account for dandisets with very large zarr
asset counts. Dandiset 002015's 37 zarrs and ~248k objects simply require
more wall-clock time than the limit allowed, regardless of normal system
load.

## Impact

- Dandiset 002015 was left in the `UNEMBARGOING` state and remained
  inaccessible to the public (the public API returns 401 for dandisets not
  in the `OPEN` state) until manually retried after the fix below.
- No data was corrupted. `unembargo_dandiset` runs inside
  `@transaction.atomic()`, so no database state from the failed attempt was
  persisted — the dandiset status was never flipped to `OPEN`.
- Some S3 objects may have already had their `embargoed` tag removed by the
  killed task before the limit fired. This is harmless but not free: a
  retry redoes the full `get_tags`/`put_tags` pair
  (`embargo/utils.py:_delete_object_tags`) for every object unconditionally
  — there's no check for whether the tag is already gone, so a retry costs
  exactly the same two S3 calls per object as a first attempt, not fewer.
  For zarr assets it's worse: `_delete_zarr_object_tags` also re-runs the
  `list_objects_v2` pagination over the whole zarr on every attempt before
  re-tagging its chunks, so a retry re-lists every zarr from scratch too.
  Because none of this is checkpointed, and the DB's `embargoed` flags were
  never updated (previous bullet), a retry selects the exact same set of
  assets/zarrs and does the exact same total amount of S3 work as an
  uninterrupted first attempt would have — the killed attempt's progress
  is entirely wasted, not resumed from.
- The task appears to have run twice for the same Celery task ID
  (`25ad4c16-…`), from two different worker dynos, 54 minutes apart. Our
  Celery configuration (`ACKS_LATE=True`, `ACKS_ON_FAILURE_OR_TIMEOUT=True`)
  is intended to acknowledge a task once it fails or times out, so a clean
  redelivery shouldn't happen. The leading theory is that the worker lost
  its RabbitMQ connection partway through the long-running task and the
  broker redelivered the unacked message to a different worker — but this
  is inference from the Sentry timestamps, not confirmed from broker logs.
  If so, the owners likely received two near-identical failure emails.

## Resolution

`unembargo_dandiset_task`'s soft time limit was increased from 20 minutes to
1 hour (PR [#2960](https://github.com/dandi/dandi-archive/pull/2960),
commit `71b02dc2`), giving roughly 2x headroom over the ~26-minute runtime
observed for this dandiset. Because a retried unembargo re-processes every
object from the start (tag removal has no resume/checkpoint mechanism), the
task must now complete in a single attempt within the new limit.

Dandiset 002015 needs to have its unembargo manually retried following this
fix, since a dandiset stuck in `UNEMBARGOING` has no automatic retry —
`kickoff_dandiset_unembargo` only accepts dandisets in the `EMBARGOED`
state.

## Follow-ups / open questions

- [ ] Confirm dandiset 002015 unembargoes successfully under the new 1-hour
      limit, and that its status reaches `OPEN`.
- [ ] Investigate whether the double execution of the same Celery task ID
      was in fact a broker-redelivery-on-timeout issue, and whether it can
      recur for other long-running tasks with `ACKS_LATE`/soft time limits.
- [ ] Consider whether tag removal should be checkpointed/resumable — e.g.
      by skipping objects whose tags are already clean, or persisting
      per-asset/per-zarr progress — so a retry (manual or automatic)
      doesn't redo the full `get_tags`/`put_tags`/zarr-listing cost for
      work a previous attempt already completed. This would also shrink
      the blast radius of any future timeout, instead of just raising the
      limit again.
- [ ] Consider whether a dandiset stuck in `UNEMBARGOING` after a task
      failure should be automatically retried or at least surfaced to
      operators, rather than relying on the owner's bug report.
