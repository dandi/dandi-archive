# S3 Backup (NESE Tape @ Dartmouth)

## Terms used

- **Primary bucket**: The sponsored bucket that is currently used for storing DANDI data. Located in us-east-2.
- **Backup bucket**: The separate bucket that stores the same data as the primary bucket, but with the Glacier Deep Archive storage class. Located in us-east-2. Does not exist yet as of this writing.

## Why is backup necessary?

The DANDI Archive hosts critical neuroscience data that represents substantial time, resource, and career investment from researchers.

While the [S3 Trailing Delete](./s3-trailing-delete.md) design protects against application-level bugs and accidental deletions within the primary bucket, it does not protect against larger-scale threats; for example, data corruption that propagates through the trailing delete rule before being detected, severe bugs in systems like garbage collection, or other unforeseen ways data might be corrupted, deleted, or otherwise lost.

A backup system provides an additional layer of data protection by maintaining a copy of the data in the primary bucket, along with a record of all ongoing changes to that data. The backup bucket will thus behave much like the tape archival systems of old, enabling administrators to "rewind" to find data in the backup bucket as it was at a given point in history.

While the [Deep Glacier design](https://github.com/dandi/dandi-archive/blob/b3e0a9df4188533723fb2ad4a95506aa724fc089/doc/design/s3-backup.md) protects against some of these same aspects, it does not protect against geographical (catastrophic destruction of physical data centers, as from natural events or otherwise; since the proposed replication bucket would be within the AWS same region), nor against denial of central AWS services by the provider(s). Having more institutionally-backed options offers greater protection through diversification of the underlying storage services used.

## Requirements

### Functional requirements

- **Replication.** Maintain a copy of the current contents of the primary bucket in the backup bucket.
- **Backup.** Replicate all primary bucket writes and deletes to the backup bucket, maintaining a tape archive backup.

### Non-functional requirements

- **Cost control.** Enable tunable controls to help keep costs reasonable for the expected data volume.

## Proposed Solution

The solution leverages the widely used [NESE Tape](https://nese.readthedocs.io/en/latest/user-docs.html#nese-tape) service provided through the [Dartmouth Discovery HPC](https://rc.dartmouth.edu/hpc/discovery-overview/):

NESE Tape provides higher density, lower cost storage, currently accessible via Globus. NESE Tape is composed of a tape system with several storage frames and 34 tape drives supporting up to 70 PB today with space available for expansion as needed.

Each NESE Tape allocation comes with a disk-based staging area that is available via Globus. Users write to the staging area and then the data is migrated to tape based on a storage lifecycle policy. The default quota on this area is 10 TB or 2% of tape capacity, whichever is larger. There is also a minimum temporary hard quota set to 4 x staging-area space to allow for short term movement of larger amounts of data.

### How It Works

Unlike the [Deep Glacier approach](https://github.com/dandi/dandi-archive/blob/b3e0a9df4188533723fb2ad4a95506aa724fc089/doc/design/s3-backup.md), some management of file transfers may be necessary, either performed by our team or by the HPV IT team, based on the NESE file transfer ruleset:

- all newly written files > 2 hr of modification time are copied to tape.
- if fileset quota > 99%; files are stubbed (replaced with a small pointer) down to 75% quota.
- files with access time age > 2 weeks are stubbed.
- files < 100 MB copied to tape, but also remain on disk.

## Limitations and Considerations

- **Upper bound on total storage**: No quota for an upper limit of long-term storage has yet been provided, aside from the grand 70 PB total of the entire NESE store; the providers claim expansion is possible as need arises.
- **Replication is eventually consistent**: No guarantees about replication speed (the time between an object finishing upload into the primary bucket and when it is available in the backup bucket) are provided. Using previous bandwidth experience to the old Dropbox backup, multi-gigabit speeds should be possible and is expected to keep up with ingest rates on the primary S3 bucket.

## Cost

Note that unlike the [Deep Glacier approach](https://github.com/dandi/dandi-archive/blob/b3e0a9df4188533723fb2ad4a95506aa724fc089/doc/design/s3-backup.md), no egress cost would be induced from the data transfer as all operations are strictly under the open data bucket.

Also note that currentt cost estimates are rough quotes provided verbatim from discussions between @yarikoptic and the Dartmouth IT team and are subject to change when/if this path solidifies.

**Below are the additional costs introduced by this backup feature** for a 1 PB primary bucket.

**Storage Costs**:

- NESE Tape storage: at the given estimate of ~$4/TB/year

$$
    \frac{\$4}{\rm{TB} \ \rm{year}} \cdot 1 \rm{PB} = \frac{\$4}{\rm{TB} \ \rm{year}} \cdot 1,000 \ \rm{TB} \cdot \frac{1 \ \rm{year}}{12 \ \rm{month}} \approx **\$333/month**
$$

where units are converted for consitency with the [Deep Glacier design](https://github.com/dandi/dandi-archive/blob/b3e0a9df4188533723fb2ad4a95506aa724fc089/doc/design/s3-backup.md).

### Future Costs

The DANDI Archive is expecting a ramp-up in data volume of 1 PB of new data over each of the next five years, culminating in a total of 6PB.

The following table shows the initial, final, intermediate, and cumulative costs for both the NESE Tape approach as well as Deep Glacier.

| Design | Year 1 (1 PB) | Year 2 (2.5 PB)[^1] | Cumulative Total<br>Over 5 years|
| :-: | :-: | :-: | :-: |
| NESE  | $4,000 / year | $10,000 / month | $14,000 |
| Deep<br>Glacier| $11,880 / year | $29,700 / year | $41,580 |

[^1]: LINC is expected to make a one-time contribution of 0.5 PB.

