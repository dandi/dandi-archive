# S3 Backup (All Options)

This document expands upon the [Deep Glacier design](https://github.com/dandi/dandi-archive/pull/2627) to include all other known alternative options with their advantages, limitations, and costs for an easy high-level comparison.



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

| Solution | Cost (TB/year) |
| :-: | :-: |
| Deep Glacier | $11.88 |
| Deep Glacier + 1 Full Restoration per Year | $14.38 |
| NESE | $4.12 |
| Granite (Internal)[^1] | $15.62 |
| Granite (External) | $24.78 |
| OSN | $12.85 |
| ORCD | $14.53 |

[^1]: Access to internal Granite pricing would require a 'liason' at Illinois.



## Cost Details

### Deep Glacier

AWS pricing is very piece-meal depending on what specific actions we need.

The basic storage has the advertised price of $0.00099/GB/month. Rescaling gives:

$$
\frac{$0.00099}{\rm{GB} \cdot \rm{month}} = \frac{$0.00099}{1 \ \rm{GB} \ 1 \ \rm{month}} \cdot \frac{1,000 \ \rm{GB}}{1 \ \rm{TB}} \cdot \frac{12 \ \rm{month}}{1 \ \rm{year}} = $11.88/\rm{TB}/\rm{year}
$$

The cost of full restoration is estimated to be about $2,500/PB, though this is largely guesswork. Amortizing this at a rate of once per year gives:

$$
\frac{$2,500}{\rm{PB} \cdot \rm{year}} = \frac{$2,500}{\rm{PB} \cdot \rm{year}} \cdot \frac{1 \ \rm{PB}}{1,000 \ \rm{TB}} = $2.5/\rm{TB}/\rm{year}
$$


### NESE

The pricing for NESE is based on the number of tapes desired for redundancy, with two being the recommended default.

It also consists of the initial tape purchase ($75) as well as required maintenance ($31.82/year).

A tape can hold 20 TB and we are assuming 'perfect fit', though this would be a practical constraint that might be hard to achieve. Expect 10-20% error for fitting assets perfectly.

Amortizing over an 8-year lifespan of a tape:

$$
\left( \frac{$75}{8 \ \rm{year}} + \frac{$31.82}{\rm{year}} \right) \frac{1}{20 \ \rm{TB} \cdot \rm{tape}} \cdot 2 \ \rm{tape} = $4.12/\rm{TB}/\rm{year}
$$



### OSN
  
OSN offers 1.4 PB for $90,000, renewing on a five-year hardware warranty. Amortizing gives:

$$
\frac{$90,000}{1.4 \ \rm{PB} \cdot 5 \ \rm{year}} = \frac{$90,000}{1.4 \ \rm{PB} \cdot 5 \ \rm{year}} \cdot \frac{1 \ \rm{PB}}{1,000 \ \rm{TB}} = $12.85/\rm{TB}/\rm{year}
$$


### ORCD

ORCD has quoted $90,000 for 1.1 PiB (usable; with RAID-Z3 reserved space), renewing on a five-year hardware warranty. Amortizing gives:

$$
\frac{$90,000}{1.1 \ \rm{PiB} \cdot 5 \ \rm{year}} = \frac{$90,000}{1.1 \ \rm{PiB} \cdot 5 \ \rm{year}}\cdot \frac{1 \ \rm{PiB}}{1.1259 \ \rm{PB}} \cdot \frac{1 \ \rm{PB}}{1,000 \ \rm{TB}} = $14.53/\rm{TB}/\rm{year}
$$



### Future Costs Over Time

The DANDI Archive is expecting a ramp-up in data volume of around 1 PB of new data over each of the next five years, culminating in a total nearing 6PB.

The following table shows the initial, final, intermediate, and cumulative costs for all backup options. 

| Design | Year 0<br>(1 PB) | Year 1<br>(2.5 PB)[^2] | Year 2<br>(3.5 PB) | Year 3<br>(4.5 PB) | Year 4<br>(5.5 PB) | Year 5<br>(6.5 PB) | Cumulative Total<br>Over All Years|
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| NESE  | $4,121 / year | $10,302.5 / year | $14,423.5 / year | $18,544.5 / year | $22,665.5 / year | $26,786.5 / year | $96,843.5 |
| Deep<br>Glacier| $11,880 / year | $29,700 / year | $41,580 / year | $53,460 / year | $65,340 / year | $77,220 / year | $279,180 |
| Deep Glacier<br>+<br>Full Restore | $14,380 / year | $35,950 / year | $50,330 / year | $64,710 / year | $79,090 / year | $93,470 / year  | max: $372,650 |
| Granite (Internal) | $15,620 / year |	$39,050 / year | $54,670 / year | $70,290 / year | $85,910 / year | $101,530 / year | $367,070 |
| Granite (External) | $24,780 / year |	$61,950 / year | $86,730 / year | $111,510 / year | $136,290 / year | $161,070 / year | $582,330 |
| OSN | $12,850/ year |	$32,125 / year | $44975 / year | $57,825 / year | $70,675 / year | $83,525 / year | $301,975 |
| ORCD | $14,530 / year |	$36,325 / year | $50,855 / year | $65385 / year | $79,915 / year | $94,445 / year | $341,455 |

[^2]: LINC is expected to make a one-time contribution of 0.5 PB.
