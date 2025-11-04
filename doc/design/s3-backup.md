# S3 Backup

## Terms used

- **Primary bucket**: The sponsored bucket that is currently used for storing DANDI data. Located in us-east-2.
- **Backup bucket**: The separate bucket that stores the same data as the primary bucket, but with the Glacier Deep Archive storage class. Located in us-east-2. Does not exist yet as of this writing.

## Why is backup necessary?

The DANDI Archive hosts critical neuroscience data that represents substantial time, resource, and career investment from researchers. While the [S3 Trailing Delete](./s3-trailing-delete.md) design protects against application-level bugs and accidental deletions within the primary bucket, it does not protect against larger-scale threats; for example, data corruption that propagates through the trailing delete rule before being detected, severe bugs in systems like garbage collection, or other unforeseen ways data might be corrupted, deleted, or otherwise lost.

A backup system provides an additional layer of data protection by maintaining a copy of the data in the primary bucket, along with a record of all ongoing changes to that data. The backup bucket will thus behave much like the tape archival systems of old, enabling administrators to "rewind" to find data in the backup bucket as it was at a given point in history.

## Requirements

### Functional requirements

- **Replication.** Maintain a copy of the current contents of the primary bucket in the backup bucket.
- **Backup.** Replicate all primary bucket writes and deletes to the backup bucket, maintaining a "tape archive" style history-based backup.

### Non-functional requirements

- **Cost control.** Enable tunable controls to help keep costs reasonable for the expected data volume.

## Proposed Solution

The solution leverages the following native S3 features to implement automatic replication with history and optional delayed deletion:

1. **S3 Replication** to copy objects from the primary bucket to a backup bucket.
2. **Delete Marker Replication** to propagate soft deletions to the backup.
3. **Bucket Versioning** on both buckets to create a history-based backup and support the replication and recovery mechanisms
4. **Optional Lifecycle Policies** on the backup bucket to permanently delete objects after a retention period

### How It Works

1. **Normal Operations**: When objects are created or updated in the primary bucket, S3 Replication automatically copies them to the backup bucket under the Glacier Deep Archive storage class.
2. **Soft Deletion**: When an object is deleted from the primary bucket, S3 creates a delete marker. This delete marker is replicated to the backup bucket, making the object appear deleted there as well.
3. **Backup**: The actual object versions remain in the backup bucket as non-current versions, hidden by the delete marker but still recoverable, forming the basis for this setup to act as a backup mechanism. Note that this design naturally tracks multiple such creation/update/deletion events by leveraging object versions.
4. **Automatic Cleanup**: An S3 Lifecycle Policy on the backup bucket monitors non-current versions and their delete markers, and permanently deletes them a certain number of days (defined as the retention period) after they become non-current, or alternatively only maintains a set number (the retention level) of non-current versions. These values can be set to a sentinel value (e.g., 0 days or 0 non-current versions) to turn off automatic cleanup. This option enables an "infinite" backup (at the cost of storing all backup objects) or a cost-tuned backup solution (by only backing up a finite amount of history).

## Distinction from Trailing Delete

This backup solution serves a different purpose than the trailing delete mechanism described in the [S3 Trailing Delete](./s3-trailing-delete.md) design. It is an additional layer of protection that operates on top of and complements the existing trailing delete mechanism. While trailing delete enables a measure of safety in the primary bucket itself, this fuller backup design offers greater data redundancy and recovery capabilities.

## Limitations and Considerations

- **Delete marker replication only works for soft deletes**: If an object version is explicitly deleted (by version ID, i.e., a “hard delete”), this deletion is NOT replicated. This does not affect DANDI, as explicit version deletion never happens in normal operations; in fact, it is explicitly disallowed via bucket policy and is deferred to a lifecycle policy (see Trailing Delete design doc for more information).
- **Replication is eventually consistent**: AWS does not provide any guarantees about replication speed (the time between an object finishing upload into the primary bucket and when it is available in the backup bucket). They offer a feature called "Replication Time Control" that guarantees a 15-minute SLA, but it's unclear if this is needed for DANDI. It costs an additional $0.015 per GB of data transferred (see [AWS docs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication-time-control.html)).
- **Existing objects are not automatically replicated**: Replication only applies to objects created or updated after replication is enabled. For existing objects, a one-time sync operation will be required.
- **Glacier Deep Archive has a minimum retention period of 180 days:** the backup bucket will use the Glacier Deep Archive storage class, as it costs substantially less than the Standard storage class ($0.00099/GB vs ~$0.20/GB, respectively), but has a minimum cost of 180 days of storage per object. That is, any retention period of less than 180 days will incur the same cost as if it were 180 days. This likely impacts the cost analysis of this design.
- **Glacier Deep Archive requires 12-48 hours to retrieve data:** the exact amount of time depends on the retrieval mechanism (see [AWS docs](https://aws.amazon.com/s3/storage-classes/glacier/)), but either way, instantaneous recovery is not possible. However, this latency is acceptable for purposes of catastrophic data recovery; it also indicates why the trailing delete mechanism continues to be valuable (it offers a much faster "data recovery" in the cases where it can be used).

## Cost

**Below are the additional costs introduced by this backup feature** for a 1 PB primary bucket (assuming both the primary bucket and backup bucket are in us-east-2). All of this information was gathered from the "Storage & requests", "Data transfer", and "Replication" tabs on [https://aws.amazon.com/s3/pricing/](https://aws.amazon.com/s3/pricing/).

**Storage Costs** (backup bucket in us-east-2):

- Glacier Deep Archive storage: ~$0.00099/GB/month
    - 1 PB = 1,024 TB × $0.99/TB = **$1,014/month**

**Data Transfer Costs**:

- Same-region data transfer between S3 buckets is free

**Retrieval Costs** (only incurred when disaster recovery is needed):

- Glacier Deep Archive retrieval:
    - $0.02/GB (standard, 12-hour retrieval)
    - $0.0025/GB (bulk retrieval, can take up to 48 hours)

### Future Costs

The DANDI Archive is expecting a ramp-up in data volume of 1 PB of new data over each of the next five years, culminating in a total of 6PB.

Scaling up the previous analysis means that the monthly costs will be projected to rise to a total of **~$6,100/month** once all of that data is seated.

An open question is whether the AWS Open Data Sponsorship program would cover the marginal costs of backup. A quick estimate shows that once all 5 PB has been uploaded, the expected bucket cost for the primary bucket (i.e., what the AWS Open Data Sponsorship program covers already, excluding backup) will be:

$$
6\ \rm{PB} \times 1024\ \rm{TB}/\rm{PB} \times 1024\ \rm{GB}/\rm{TB} \times \$0.021/GB/mo \approxeq \$130000/mo
$$

while the associated backup costs would represent only $`\$31000 / \$660000 \approxeq 4.6\%`$ of the cost of the storage itself.
