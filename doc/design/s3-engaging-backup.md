# S3 Backup to MIT Engaging 

## Proposed Solution For Initial Backup from S3 to Server 
Use s5cmd or Globus to perform a full sync from S3 to the storage server.
### s5cmd 

### Globus 



## Proposed Solution for Incremental Sync from S3 to Server 

### s5cmd sync
**How the `sync` Command Works:** <br>
`sync` command synchronizes S3 buckets, prefixes, directories and files between S3 buckets and prefixes as well. It compares files between source and destination, taking source files as source-of-truth. It makes a one way synchronization from source to destination without modifying any of the source files and deleting any of the destination files (unless `--delete flag` has passed).

It *only* copies files that: 
- Do not exist in destination destination
- Sync strategy allows
    - Default: By default `s5cmd` compares files' both size *and* modification times, treating source files as source of truth. Any difference in size or modification time would cause s5cmd to copy source object to destination.
    - Size only: With `--size-only` flag, it's possible to use the strategy that would only compare file sizes. Source treated as source of truth and any difference in sizes would cause s5cmd to copy source object to destination.


**Scheduling the Sync** <br>
Can automate S3 to Engaging sync with a cron job on the server to run the s5cmd sync command at regular intervals (e.g., daily or hourly).

**Limitations** <br>
s5cmd does not natively support bidirectional sync. However, it is very efficient for one-way sync from S3 to server.