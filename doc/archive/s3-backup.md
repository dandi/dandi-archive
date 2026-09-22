# S3 Backup

# ARCHIVED

On 5/18/2026, it was determined that there is no funding capabilities for any S3 backup option at this point in time.



### Contents

- [Proposed Solutions](#proposed-solutions)
  - [S3 Replication (Deep Glacier)](#s3-replication-deep-glacier)
  - [Tape](#tape)
  - [Institutional Servers](#institutional-servers)
  - [Distributed](#distributed)
- [General Considerations](#general-considerations)
- [How They Work](#how-they-work)
- [Specific Advantages and Limitations](#specific-advantages-and-limitations)
- [Cost Summary](#cost-summary)
- [Cost Details](#cost-details)
- [Future Costs Over Time](#future-costs-over-time)


## Why is backup necessary?

The DANDI Archive hosts critical neuroscience data that represents substantial time, resource, and career investment from researchers.

While the [S3 Trailing Delete](./s3-trailing-delete.md) design protects against application-level bugs and accidental deletions within the primary bucket, it does not protect against larger-scale threats; for example, data corruption that propagates through the trailing delete rule before being detected, severe bugs in systems like garbage collection, or other unforeseen ways data might be corrupted, deleted, or otherwise lost.

A backup system provides an additional layer of data protection by maintaining a copy of the data in the primary bucket, along with a record of all ongoing changes to that data. The backup bucket will thus behave much like the tape archival systems of old, enabling administrators to "rewind" to find data in the backup bucket as it was at a given point in history.



## Requirements

### Functional requirements

- **Replication**: Maintain a copy of the current contents of the primary bucket in the backup bucket.
- **Backup**: Replicate all primary bucket writes and deletes to the backup bucket, maintaining a tape archive backup.

### Non-functional requirements

- **Cost control**: Enable tunable controls to help keep costs reasonable for the expected data volume.



## Proposed Solutions

### S3 Replication (Deep Glacier)
This is thoroughly discussed in the [Deep Glacier design](https://github.com/dandi/dandi-archive/pull/2627).

### Tape
Tape is one of the more classical methods of backing up such large quantities of data. Two known services utilize this method:
- **[NESE](https://nese.readthedocs.io/en/latest/user-docs.html#nese-tape)**: This is composed of a tape system with several storage frames and 34 tape drives supporting up to 70 PB today, with space available for expansion as needed. A Globus-based portal would be provided for us through the [Dartmouth Discovery HPC](https://rc.dartmouth.edu/hpc/discovery-overview/).
- **[Granite](https://docs.ncsa.illinois.edu/systems/granite/en/latest/index.html)**: This is made up of a single Spectra TFinity Plus library running Specta’s LumOS library software. This 19-frame library is capable of holding over 300PB of replicated data, leveraging 20 LTO-9 tape drives to transfer data to/from thousands of LTO-9 (18TB) tapes.

### Institutional Servers
- **[Open Storage Network (OSN)](https://www.openstoragenetwork.org/get-involved/get-a-pod/)**: This data is housed in storage pods interconnected by national, high-performance networks creating well-connected, cloud-like storage that is easily accessible at high data transfer rates comparable to or exceeding the public cloud storage providers, where users can temporariy park data, for retrieval by a collaborator or create a repository of active research data.
- **[ORCD](https://orcd.mit.edu/)**: This is MIT's primary HPC and is the location of our current mirror of the bucket.

### Distributed
Another proposed option (by Chris Hill at MIT) is to leverage more of a distributed/peer-to-peer system to crowdsource this problem:
- **[Bacula](https://en.wikipedia.org/wiki/Bacula)**: This is an open-source, enterprise-level computer backup system for heterogeneous networks. It is designed to automate backup tasks that had often required intervention from a systems administrator or computer operator. Note that it is merely software for managing the distribution, and the hardware would be wherever we have friends who have disk space to contribute.



## General Considerations

**Geographical sources of data loss**: The AWS approach illustrated in [Deep Glacier design](https://github.com/dandi/dandi-archive/pull/2627) would necessarily place the backup bucket within the same AWS region, and therefore would not protect against any geographical issues, such as catastrophic destruction of physical data centers (as from natural events or otherwise).

**Diversification of service providers**: The AWS approach illustrated in [Deep Glacier design](https://github.com/dandi/dandi-archive/pull/2627) would deepen the vendor lock-in, which increases our vulnerability to provider-based supply chain attacks, including denial of central AWS services by the provider(s). Having more institutionally-backed options offers greater protection through diversification of the underlying services used.

**Sustainability**: Virtually every non-AWS solution must be 'refreshed' over time. Tape must be re-copied every 8 years or so. All physical disks on servers must be replaced every 5 years to stay within warranty (required or recommended by maintenance staff). There is effectively no permanent solution aside from AWS (which presumably manages such things ephemerally) or the distributed approach (which requires continued active participation by the community). As such, all cost estimates are expressed in units of time (per year), but this can clearly only be supported for as long as there is sustained, designated funding within the budget for data backup purposes.



## How They Work

### Deep Glacier

Various 'buttons' would be pressed in the AWS console (or explicitly coded in Terraform). See https://github.com/dandi/dandi-archive/pull/2627 for more details.

The objects from our primary S3 bucket would be automatically replicated onto a second bucket in the same region, but with all assets being directly deposited to the Deep Glacier lifecycle state for reduced cost.

The AWS service would theoretically handle all data management automatically, including S3-specific attributes such as object tags.


### NESE/Granite

With this approach, some minimal management of file transfers would be necessary. Using Globus, objects from the S3 bucket would be transferred to the intermediate NESE disk staging storage while awaiting the following transfer to tape. This leaves 'stub' files as records that an object was copied.

Globus has a simple interface for creating automated rulesets (such as sync operations); they also have an API if a code-based solution (similar to [Simple S3 Backup (`s5cmd`-based)](https://github.com/dandi/simple-s3-backup/tree/main) or [s3invsync](https://github.com/dandi/s3invsync)) is preferred.


### OSN/ORCD/Bacula

These would all act essentially the same as a remote server or general HPC. All file management would be performed by internally controlled code and run on CRON.



## Specific Advantages and Limitations

Any solutions not listed here have no known limitations, though this is likely because exact public details of the underlying mechanisms are absent.

### Deep Glacier

- **Advantages**:
  - Speed of data transfer is expected to be orders of magnitude faster than any other solution.
  - Constant cost model; can be easily enabled or disabled as budget allows.

- **Limitations**:
  - Some minor engineering effort should still be undertaken to ensure there is a known process for using the service to perform targeted restorations of objects from the bucket.


### Tape (NESE/Granite)

- **Advantages**:
  - Among the non-AWS solutions, tape has a very high upper bound on total storage size; essentially, as much as we are willing to pay for, they can provide. This reaches into the hundreds of PB.
  - Tape has the lowest overall cost, and NESE has the lowest cost among tape services.

- **Limitations**:
  - Some engineering effort would be required on our end to monitor the file management process and ensure feasibility. This would certainly be more effort than the Deep Glacier approach.
  - Throughput speeds are not known but assumed to be slow. A full restoration of the S3 bucket would take time to complete.
  - NESE has a maximum file size of 1 TiB.
  - NESE has a maximum number of objects must be less than $\frac{\text{total size}}{100 \text{ MB}}$.
  - Granite has a ratio of 1 TB to 10,000 inodes.


### Servers (OSN/ORCD)

- **Advantages**:
  - Expected to have the highest data transfer speeds among non-AWS solutions. A full restoration would not take very long.
  - Objects from the S3 bucket would be stored in locations that possess fast disk speeds and various levels of local compute, which could be leveraged for useful purposes.

- **Limitations**:
  - More engineering effort would be required on our end to monitor the file management process and ensure feasibility. This would certainly be more effort than the tape approach.
  - Significantly more expensive than any other solution.
  - Storage expansions must be performed in bulk units of multiple PB at a time.
  - Storage expansions will likely take time to order and install - estimates range from 1-3 months until ready to use.
  - Storage expansions must be renewed every 5 years to stay within warranty.


### Distributed System (Bacula)

- **Advantages**:
  - Could theoretically be the safest way of disseminating the data (with multiple redundancies).
  - Could instill a deeper sense of community by allowing every user the chance to participate in the DANDI infrastructure.
  - Storage and data transfer costs are offloaded to volunteers and their resources.

- **Limitations**:
  - This would be a significant engineering endeavor. Probably close to a full year-long project for a single engineer, at least.



## Cost Summary

All sizes below use binary (IEC) prefixes: 1 TiB = 1,024 GiB, 1 PiB = 1,024 TiB. Note that AWS advertises its prices "per GB", but actually bills per GiB ($2^{30}$ bytes).

| Solution | Cost (TiB/year) |
| :-: | :-: |
| Deep Glacier | $12.17 |
| Deep Glacier + 1 Full Restoration per Year | $14.61 |
| NESE | $4.53 |
| Granite (Internal)[^1] | $17.17 |
| Granite (External) | $27.25 |
| OSN | $14.14 |
| ORCD | $15.98 |

[^1]: Access to internal Granite pricing would require a 'liason' at Illinois. Granite prices are quoted per (decimal) TB ($15.62/TB/year internal, $24.78/TB/year external) and have been converted using 1 TiB = 1.0995 TB.



## Cost Details

### Deep Glacier

AWS pricing is very piece-meal depending on what specific actions we need.

The basic storage has the advertised price of $0.00099/GB/month, where AWS's "GB" is in fact a GiB. Rescaling gives:

$$
\frac{$0.00099}{\rm{GiB} \cdot \rm{month}} = \frac{$0.00099}{1 \ \rm{GiB} \ 1 \ \rm{month}} \cdot \frac{1,024 \ \rm{GiB}}{1 \ \rm{TiB}} \cdot \frac{12 \ \rm{month}}{1 \ \rm{year}} = $12.17/\rm{TiB}/\rm{year}
$$

The cost of full restoration is estimated to be about $2,500/PiB, though this is largely guesswork. Amortizing this at a rate of once per year gives:

$$
\frac{$2,500}{\rm{PiB} \cdot \rm{year}} = \frac{$2,500}{\rm{PiB} \cdot \rm{year}} \cdot \frac{1 \ \rm{PiB}}{1,024 \ \rm{TiB}} = $2.44/\rm{TiB}/\rm{year}
$$


### NESE

The pricing for NESE is based on the number of tapes desired for redundancy, with two being the recommended default.

It also consists of the initial tape purchase ($75) as well as required maintenance ($31.82/year).

A tape can hold 20 TB (decimal, i.e., $20 \times 10^{12}$ bytes $\approx$ 18.19 TiB) and we are assuming 'perfect fit', though this would be a practical constraint that might be hard to achieve. Expect 10-20% error for fitting assets perfectly.

Amortizing over an 8-year lifespan of a tape:

$$
\left( \frac{$75}{8 \ \rm{year}} + \frac{$31.82}{\rm{year}} \right) \frac{1}{18.19 \ \rm{TiB} \cdot \rm{tape}} \cdot 2 \ \rm{tape} = $4.53/\rm{TiB}/\rm{year}
$$



### OSN

OSN offers 1.4 PB (decimal, $\approx$ 1.2434 PiB) for $90,000, renewing on a five-year hardware warranty. Amortizing gives:

$$
\frac{$90,000}{1.4 \ \rm{PB} \cdot 5 \ \rm{year}} = \frac{$90,000}{1.4 \ \rm{PB} \cdot 5 \ \rm{year}} \cdot \frac{1 \ \rm{PB}}{0.8882 \ \rm{PiB}} \cdot \frac{1 \ \rm{PiB}}{1,024 \ \rm{TiB}} = $14.14/\rm{TiB}/\rm{year}
$$


### ORCD

ORCD has quoted $90,000 for 1.1 PiB (usable; with RAID-Z3 reserved space), renewing on a five-year hardware warranty. Amortizing gives:

$$
\frac{$90,000}{1.1 \ \rm{PiB} \cdot 5 \ \rm{year}} = \frac{$90,000}{1.1 \ \rm{PiB} \cdot 5 \ \rm{year}} \cdot \frac{1 \ \rm{PiB}}{1,024 \ \rm{TiB}} = $15.98/\rm{TiB}/\rm{year}
$$



### Future Costs Over Time

The DANDI Archive is expecting a ramp-up in data volume of around 1 PiB of new data over each of the next five years, culminating in a total nearing 6 PiB.

The following table shows the initial, final, intermediate, and cumulative costs for all backup options (computed from the unrounded per-TiB rates above and rounded to the nearest dollar).

| Design | Year 0<br>(1 PiB) | Year 1<br>(2.5 PiB)[^2] | Year 2<br>(3.5 PiB) | Year 3<br>(4.5 PiB) | Year 4<br>(5.5 PiB) | Year 5<br>(6.5 PiB) | Cumulative Total<br>Over All Years|
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| NESE | $4,638 / year | $11,595 / year | $16,234 / year | $20,872 / year | $25,510 / year | $30,148 / year | $108,997 |
| Deep<br>Glacier | $12,457 / year | $31,143 / year | $43,600 / year | $56,057 / year | $68,514 / year | $80,971 / year | $292,742 |
| Deep Glacier<br>+<br>Full Restore | $14,957 / year | $37,393 / year | $52,350 / year | $67,307 / year | $82,264 / year | $97,221 / year | max: $351,492 |
| Granite (Internal) | $17,587 / year | $43,966 / year | $61,553 / year | $79,140 / year | $96,726 / year | $114,313 / year | $413,285 |
| Granite (External) | $27,900 / year | $69,749 / year | $97,649 / year | $125,549 / year | $153,449 / year | $181,349 / year | $655,645 |
| OSN | $14,476 / year | $36,190 / year | $50,665 / year | $65,141 / year | $79,617 / year | $94,093 / year | $340,182 |
| ORCD | $16,364 / year | $40,909 / year | $57,273 / year | $73,636 / year | $90,000 / year | $106,364 / year | $384,546 |

[^2]: LINC is expected to make a one-time contribution of 0.5 PiB.
