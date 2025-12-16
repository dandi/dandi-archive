# S3 Backup (Non-AWS)

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

The solution leverages one of the widely used [NESE Tape](https://nese.readthedocs.io/en/latest/user-docs.html#nese-tape) (provided through the [Dartmouth Discovery HPC](https://rc.dartmouth.edu/hpc/discovery-overview/)), [Granite](https://docs.ncsa.illinois.edu/systems/granite/en/latest/index.html), or [Open Storage Network](https://www.openstoragenetwork.org/get-involved/get-a-pod/) services:

NESE Tape provides higher density, lower cost storage, currently accessible via Globus. NESE Tape is composed of a tape system with several storage frames and 34 tape drives supporting up to 70 PB today with space available for expansion as needed.

Each NESE Tape allocation comes with a disk-based staging area that is available via Globus. Users write to the staging area and then the data is migrated to tape based on a storage lifecycle policy. The default quota on this area is 10 TB or 2% of tape capacity, whichever is larger. There is also a minimum temporary hard quota set to 4 x staging-area space to allow for short term movement of larger amounts of data.

Granite is made up of a single Spectra TFinity Plus library running Specta’s LumOS library software. This 19-frame library is capable of holding over 300PB of replicated data, leveraging 20 LTO-9 tape drives to transfer data to/from thousands of LTO-9 (18TB) tapes.



### How It Works

Unlike the [Deep Glacier approach](https://github.com/dandi/dandi-archive/blob/b3e0a9df4188533723fb2ad4a95506aa724fc089/doc/design/s3-backup.md), some management of file transfers may be necessary, either performed by our team or by the HPV IT team, based on the NESE file transfer ruleset:

- all newly written files > 2 hr of modification time are copied to tape.
- if fileset quota > 99%; files are stubbed (replaced with a small pointer) down to 75% quota.
- files with access time age > 2 weeks are stubbed.
- files < 100 MB copied to tape, but also remain on disk.



## Limitations and Considerations

- **Upper bound on total storage**: No quota for an upper limit of long-term storage has yet been provided, aside from the grand 70 PB total of the entire NESE store and 300 PB for Granite; the providers claim expansion is possible as need arises.
- **Maximum file size**: NESE tape services do place a maximum file size limitation of 1 TiB; though no single file on DANDI would violate this (some might come close though). No limitation has been relayed for Granite or others.
- **Replication is eventually consistent**: No guarantees about replication speed (the time between an object finishing upload into the primary bucket and when it is available in the backup bucket) are provided. Using previous bandwidth experience to the old Dropbox backup, multi-gigabit speeds should be possible and is expected to keep up with ingest rates on the primary S3 bucket.



## Cost

Note that unlike the [Deep Glacier approach](https://github.com/dandi/dandi-archive/blob/b3e0a9df4188533723fb2ad4a95506aa724fc089/doc/design/s3-backup.md), no egress cost would be induced from the data transfer as all operations are strictly under the open data bucket.

Also note that current cost estimates are rough quotes provided verbatim from discussions between @yarikoptic and the Dartmouth IT team and are subject to change when/if this path solidifies.

**Below are the additional costs introduced by this backup feature** for a 1 PB primary bucket.

**Storage Costs**:

- NESE Tape storage: at the given estimate of ~$4/TB/year

$$
    \frac{\$4}{\rm{TB} \ \rm{year}} \cdot 1 \rm{PB} = \frac{\$4}{\rm{TB} \ \rm{year}} \cdot 1,000 \ \rm{TB} \cdot \frac{1 \ \rm{year}}{12 \ \rm{month}} \approx **\$333/month**
$$

- Granite (internal pricing; would require a 'liaison') storage: at the given estimate of ~$15.62/TB/year

$$
    \frac{\$15.62}{\rm{TB} \ \rm{year}} \cdot 1 \rm{PB} = \frac{\$15.62}{\rm{TB} \ \rm{year}} \cdot 1,000 \ \rm{TB} \cdot \frac{1 \ \rm{year}}{12 \ \rm{month}} \approx **\$1,301.66/month**
$$

- Granite (external) storage: at the given estimate of ~$24.78/TB/year

$$
    \frac{\$24.78}{\rm{TB} \ \rm{year}} \cdot 1 \rm{PB} = \frac{\$24.78}{\rm{TB} \ \rm{year}} \cdot 1,000 \ \rm{TB} \cdot \frac{1 \ \rm{year}}{12 \ \rm{month}} \approx **\$2,065/month**
$$

where units are converted for consistency with the [Deep Glacier design](https://github.com/dandi/dandi-archive/blob/b3e0a9df4188533723fb2ad4a95506aa724fc089/doc/design/s3-backup.md).



### Future Costs

The DANDI Archive is expecting a ramp-up in data volume of around 1 PB of new data over each of the next five years, culminating in a total nearing 6PB.

The following table shows the initial, final, intermediate, and cumulative costs for both the NESE Tape approach as well as Deep Glacier.

| Design | Year 0<br>(1 PB) | Year 1<br>(2.5 PB)[^1] | Year 2<br>(3.5 PB) | Year 3<br>(4.5 PB) | Year 4<br>(5.5 PB) | Year 5<br>(6.5 PB) | Cumulative Total<br>Over All Years|
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| NESE  | $4,000 / year | $10,000 / year | $14,000 / year | $18,000 / year | $22,000 / year | $26,000 / year | $94,000 |
| Deep<br>Glacier| $11,880 / year | $29,700 / year | $41,580 / year | $53,460 / year | $65,340 / year | $77,220 / year | $279,180 |
| Deep Glacier<br>+<br>Full Restore[^2] | $14,380 / year | $35,950 / year | $50,330 / year | $64,710 / year | $79,090 / year | $93,470 / year  | max: $372,650 |
| Granite (Internal) | $15,620 / year |	$39,050 / year | $54,670 / year | $70,290 / year | $85,910 / year | $101,530 / year | $367,070 |
| Granite (External) | $24,780 / year |	$61,950 / year | $86,730 / year | $111,510 / year | $136,290 / year | $161,070 / year | $582,330 |

[^1]: LINC is expected to make a one-time contribution of 0.5 PB.
[^2]: In the event that a full restoration of the bucket is required once during the year indicated by the column, the Deep Glacier approach has additional costs to just the underlying storage.
