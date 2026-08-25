# State of Garbage Collection

> **TLDR:** The garbage collection machinery is designed, implemented, and largely merged. However, the automated daily task has never been switched on because unattended deletion was deemed unsafe without a backup of the archive, and S3 Replication based backup has been deemed too expensive. We propose unblocking GC by extending the already-deployed S3 "undelete" recovery window (e.g., to 180 days), which protects against application bugs comparably to a backup, without incurring any additional AWS costs.

## Current state of garbage collection

Garbage collection (GC) for DANDI has been designed and built incrementally over several years ([overview of the GC types](https://github.com/dandi/dandi-archive/blob/master/doc/design/garbage-collection-1.md)). To summarize the current state:

- **S3 trailing delete ("undelete"): deployed.** With [S3 trailing delete](https://github.com/dandi/dandi-archive/blob/master/doc/design/s3-trailing-delete.md) already deployed, the production bucket is versioned: deleting an object only places a delete marker, a lifecycle rule permanently expires deleted objects 30 days later, and the `PreventDeletionOfDeleteMarkers` bucket policy denies `s3:DeleteObjectVersion` to all principals, preventing all IAM users and roles (including the DANDI API server) from being able to permanently delete objects; only the bucket lifecycle rule is permitted to do that. This affords a strong level of protection against accidental data loss via, e.g., mistakes by principals and bugs in application code.
- **`Upload` / `AssetBlob` GC: implemented and merged, but not enabled.** [Design](https://github.com/dandi/dandi-archive/blob/master/doc/design/garbage-collection-uploads-asset-blobs-2.md) and [implementation (PR #2087, merged January 2025)](https://github.com/dandi/dandi-archive/pull/2087). The logic for orphaned uploads and asset blobs to be deleted after a 7-day grace period is implemented, with every deletion being recorded in `GarbageCollectionEvent` audit tables so it can be restored during the trailing-delete window. The beat cron it runs on is currently disabled and has never been turned on in production.
- **Manual GC command: merged.** [`collect_garbage` (PR #2343)](https://github.com/dandi/dandi-archive/pull/2343) lets an operator run GC on demand, with explicit confirmation prompts. This is currently the **only** way GC runs.
- **`Asset` GC: implemented, not yet merged.** The [design (PR #2367)](https://github.com/dandi/dandi-archive/pull/2367) and [implementation (PR #2368)](https://github.com/dandi/dandi-archive/pull/2368) are open and awaiting review.

## Why is backup a prerequisite?

Enabling the GC cron means the application deletes data from the bucket on a schedule, with no human in the loop. For safety reasons, a full backup of the archive was treated as a prerequisite for automated GC, and the GC effort has been stalled behind backup ever since.

The original backup design is inlined in full at the bottom of this page for reference, with some updates to cost numbers due to differences in expected data size since the original design was written. A broader survey of backup options (S3 Replication, tape at NESE and Granite, institutional storage at OSN and ORCD, and a distributed community system) was later written up in [doc/archive/s3-backup.md](https://github.com/dandi/dandi-archive/blob/master/doc/archive/s3-backup.md).

On May 18, 2026, per the design doc, it was determined that there is no funding for any non-sponsored backup option at this time. Even the cheapest option surveyed (NESE tape, ~$4.12/TB/year) reaches roughly $27,000/year at the projected ~6.5 PB archive size, and the AWS Deep Glacier option roughly $77,000/year.

## Proposal: unblock GC with an extended "undelete" recovery window

The S3 undelete mechanism is already deployed. We propose extending its recovery window—e.g., setting the trailing-delete lifecycle rule to permanently expire deleted objects after a larger time window than 30 days—and accepting that, combined with the existing bucket policy, as the safety net for automated GC.

**Why is this affordable vs. a separate backup bucket?**

A backup/S3 replication stores a second copy of the entire bucket, in what would have to be a separate AWS account since the AWS Open Data Sponsorship program will not cover backup costs. An extended recovery window retains deleted data in the sponsored bucket for a limited amount of time before deleting it; this means this data will fall under the billing of the sponsored account and will not incur separate costs.

**Why is this a suitable replacement for backup?**

The backup design derives much of its safety from the backup bucket being unreachable by any IAM users/roles, the most sensitive of those being the role assumed by the DANDI API server running on Heroku; this offers strong guarantees that application bugs can never touch it. The undelete mechanism offers a near equivalent guarantee against that same threat, because of the distinction between S3's two delete operations:

- `s3:DeleteObject` - the only deletion the application ever performs. On a versioned bucket this does not destroy any data; it merely places a delete marker, and the object remains fully recoverable.
- `s3:DeleteObjectVersion` - the operation that actually destroys data. The existing `PreventDeletionOfDeleteMarkers` bucket policy denies this action to all principals, including the DANDI API server and any credentials it holds.

Even a worst-case GC bug that "deleted" every object in the bucket could not permanently destroy anything: all of it would remain recoverable for the full window. Permanent deletion happens only via the S3 lifecycle rule. Actually destroying data would require an administrator to first deliberately remove the protective bucket policy, the same level of deliberate administrative action it would take to destroy a backup bucket in another AWS account.

**Tradeoffs of accepting no true backup**

What a backup potentially adds beyond what is mentioned above is protection against threats like malicious behavior of DANDI admins or compromise of the AWS account by outside actors. However, we've already established that these scenarios are outside of the threat model, and aren't something the backup design exists to prevent in the first place.

## Proposal: develop `fsck`-style scripts to monitor GC health

In addition to implementing a longer recovery window, we propose to create an "fsck" style script that can report inconsistencies in the garbage collection state between the application database and the S3 bucket. Such a script can run on a schedule and would report the following items:

- Live `Asset` objects with no corresponding `AssetBlob`
- Live `AssetBlob` objects with no corresponding live S3 object
- `GarbageCollectionEventRecord` objects with no corresponding deleted S3 object
- Live S3 objects that are not already slated for garbage collection

Any of the above categories would indicate an error in the garbage collection logic, or some other issue that needs to be addressed. If such problems are reported within the recovery window, they can be corrected by hand.

## What remains to get GC fully live (assuming no funding for backup/we're relying on undelete)

1. **Implement the `fsck` script(s)** - this will help us keep the system healthy and, in particular, prevent catastrophic data loss.
2. **Extend the recovery window (if applicable)** - if we decide to accept extended recovery window instead of backup, we'll need a Terraform change to the trailing-delete lifecycle rule (30 → whatever we decide on days [here](https://github.com/dandi/dandi-infrastructure/blob/5ead0bd081b18082ccd8741ece8da19197cb631e/terraform/modules/dandiset_bucket/main.tf#L296-L299)), keeping the GC code's restoration window aligned with it.
3. **Merge `Asset` GC** - review and land PRs [#2367](https://github.com/dandi/dandi-archive/pull/2367) and [#2368](https://github.com/dandi/dandi-archive/pull/2368).
4. **Enable the daily task** - uncomment the beat schedule, schedule the `fsck` scripts to run, and monitor the first runs.

---

## Appendix: original backup design (inlined for reference)

*This is the original "S3 backup via Deep Glacier replication" design referenced above. The cost projections at the bottom were updated in August 2026 to reflect the current data-volume forecast (~1 PB/year of growth, ~6.5 PB total after five years - see [doc/archive/s3-backup.md](https://github.com/dandi/dandi-archive/blob/master/doc/archive/s3-backup.md)).*

### Terms used

- **Primary bucket**: The sponsored bucket that is currently used for storing DANDI data
- **Backup bucket**: The separate bucket that stores the same data as the primary bucket, but in a different region with the Glacier Deep Archive storage class. Does not exist yet as of this writing.

### Why is backup necessary?

The DANDI Archive hosts critical neuroscience data that represents substantial time, resource, and career investment from researchers. While the [S3 Trailing Delete](https://github.com/dandi/dandi-archive/blob/master/doc/design/s3-trailing-delete.md) design protects against application-level bugs and accidental deletions within the primary bucket, it does not protect against larger-scale threats; for example, data corruption that propagates through the trailing delete rule before being detected, severe bugs in systems like garbage collection, or other unforeseen ways data might be corrupted, deleted, or otherwise lost.

A backup system provides an additional layer of data protection by maintaining a copy of the data in the primary bucket, along with a record of all ongoing changes to that data. The backup bucket will thus behave much like the tape archival systems of old, enabling administrators to "rewind" to find data in the backup bucket as it was at a given point in history.

### Requirements

#### Functional requirements

- **Replication.** Maintain a copy of the current contents of the primary bucket in the backup bucket.
- **Backup.** Replicate all primary bucket writes and deletes to the backup bucket, maintaining a "tape archive" style history-based backup.

#### Non-functional requirements

- **Cost control.** Enable tunable controls to help keep costs reasonable for the expected data volume.

### Proposed Solution

The solution leverages the following native S3 features to implement automatic replication with history and optional delayed deletion:

1. **S3 Replication** to copy objects from the primary bucket to a backup bucket.
2. **Delete Marker Replication** to propagate soft deletions to the backup.
3. **Bucket Versioning** on both buckets to create a history-based backup and support the replication and recovery mechanisms
4. **Optional Lifecycle Policies** on the backup bucket to permanently delete objects after a retention period

#### How It Works

1. **Normal Operations**: When objects are created or updated in the primary bucket, S3 Replication automatically copies them to the backup bucket under the Glacier Deep Archive storage class.
2. **Soft Deletion**: When an object is deleted from the primary bucket, S3 creates a delete marker. This delete marker is replicated to the backup bucket, making the object appear deleted there as well.
3. **Backup**: The actual object versions remain in the backup bucket as non-current versions, hidden by the delete marker but still recoverable, forming the basis for this setup to act as a backup mechanism. Note that this design naturally tracks multiple such creation/update/deletion events by leveraging object versions.
4. **Automatic Cleanup**: An S3 Lifecycle Policy on the backup bucket monitors non-current versions and their delete markers, and permanently deletes them a certain number of days (defined as the retention period) after they become non-current, or alternatively only maintains a set number (the retention level) of non-current versions. These values can be set to a sentinel value (e.g., 0 days or 0 non-current versions) to turn off automatic cleanup. This option enables an "infinite" backup (at the cost of storing all backup objects) or a cost-tuned backup solution (by only backing up a finite amount of history).

### Distinction from Trailing Delete

This backup solution serves a different purpose than the trailing delete mechanism described in the [S3 Trailing Delete](https://github.com/dandi/dandi-archive/blob/master/doc/design/s3-trailing-delete.md) design. It is an additional layer of protection that operates on top of and complements the existing trailing delete mechanism. While trailing delete enables a measure of safety in the primary bucket itself, this fuller backup design offers greater data redundancy and recovery capabilities.

### Limitations and Considerations

- **Delete marker replication only works for soft deletes**: If an object version is explicitly deleted (by version ID, i.e., a "hard delete"), this deletion is NOT replicated. This does not affect DANDI, as explicit version deletion never happens in normal operations; in fact, it is explicitly disallowed via bucket policy and is deferred to a lifecycle policy (see Trailing Delete design doc for more information).
- **Replication is eventually consistent**: AWS does not provide any guarantees about replication speed (the time between an object finishing upload into the primary bucket and when it is available in the backup bucket). They offer a feature called "Replication Time Control" that guarantees a 15-minute SLA, but it's unclear if this is needed for DANDI. It costs an additional $0.015 per GB of data transferred (see [https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication-time-control.html](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication-time-control.html)).
- **Existing objects are not automatically replicated**: Replication only applies to objects created or updated after replication is enabled. For existing objects, a one-time sync operation will be required.
- **Glacier Deep Archive has a minimum retention period of 180 days**: the backup bucket will use the Glacier Deep Archive storage class, as it costs substantially less than the Standard storage class ($0.00099/GB vs ~$0.20/GB, respectively), but has a minimum cost of 180 days of storage per object. That is, any retention period of less than 180 days will incur the same cost as if it were 180 days. This likely impacts the cost analysis of this design.
- **Glacier Deep Archive requires 12-48 hours to retrieve data**: the exact amount of time depends on the retrieval mechanism (see [https://aws.amazon.com/s3/storage-classes/glacier/](https://aws.amazon.com/s3/storage-classes/glacier/)), but either way, instantaneous recovery is not possible. However, this latency is acceptable for purposes of catastrophic data recovery; it also indicates why the trailing delete mechanism continues to be valuable (it offers a much faster "data recovery" in the cases where it can be used).

### Cost

**Below are the additional costs introduced by this backup feature** for a 1 PB primary bucket (assuming both the primary bucket and backup bucket are in us-east-2). All of this information was gathered from the "Storage & requests", "Data transfer", and "Replication" tabs on [https://aws.amazon.com/s3/pricing/](https://aws.amazon.com/s3/pricing/).

**Storage Costs** (backup bucket in us-east-2):

- Glacier Deep Archive storage: ~$0.00099/GB/month
  - 1 PB = 1,024 TB × $0.99/TB = **$1,014/month**

**Data Transfer Costs**:

- Same-region data transfer between S3 buckets is free

**Retrieval Costs** (only incurred when disaster recovery is needed):

- Glacier Deep Archive retrieval:
  - $0.02/GB (standard, 12-hour retrieval)
  - $0.025/GB (bulk retrieval, can take up to 48 hours)

#### Future Costs

The DANDI Archive is expecting a ramp-up in data volume of around 1 PB of new data over each of the next five years (plus an expected one-time contribution of 0.5 PB from LINC), culminating in a total nearing 6.5 PB (see [doc/archive/s3-backup.md](https://github.com/dandi/dandi-archive/blob/master/doc/archive/s3-backup.md) for the full cost survey based on this projection).

Using the Deep Glacier rate of $11.88/TB/year, the projected additional cost of backup over the ramp-up is (from the [cost survey's projections](https://github.com/dandi/dandi-archive/blob/master/doc/archive/s3-backup.md#future-costs-over-time)):

| Year 0 (1 PB) | Year 1 (2.5 PB) | Year 2 (3.5 PB) | Year 3 (4.5 PB) | Year 4 (5.5 PB) | Year 5 (6.5 PB) | Cumulative |
| ------------- | --------------- | --------------- | --------------- | --------------- | --------------- | ---------- |
| $11,880 / year | $29,700 / year | $41,580 / year | $53,460 / year | $65,340 / year | $77,220 / year | $279,180 |

At the year-5 volume, backup costs about $77,220/year (~$6,400/month) — far below the ~$31,000/month projected under the earlier 30 PB growth forecast, but still beyond available funding as of the May 2026 review.

Note that these figures are purely the *additional* cost of backup; the cost of the primary bucket itself is excluded, since it is covered by the AWS Open Data Sponsorship Program.
