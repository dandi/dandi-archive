# S3 Trailing Delete

## Why is "trailing delete" necessary?

The core value of the DANDI Archive comes from the data we host. The process for getting this data into DANDI often involves coordination between several people to get an extremely large volume of data annotated with useful metadata and uploaded to our system. Because of the amount of time and work involved in this process, we need to minimize the risk of accidental data loss to the greatest extent that is possible and reasonable. Additionally, we would like to implement “garbage collection” in the future, which involves programmatically clearing out stale asset blobs from S3. All of this leads to a desire to be able to recover an s3 object that has been deleted.

Our ultimate goal is to prevent data loss from application programming errors. With protection such as a trailing delete capability, we will be safer in implementing application features that involve intentional deletion of data. Any bugs we introduce while doing so are far less likely to destroy data that was not supposed to be deleted.

The original GitHub issue around this feature request can be found at [https://github.com/dandi/dandi-archive/issues/524](https://github.com/dandi/dandi-archive/issues/524). Although the issue asks for a Deep Glacier storage tier, the design in this document solves the underlying problem differently (and in a more robust way). Below we address the possible usage of a Deep Glacier tiered bucket as a solution to the orthogonal problem of data **backup** which addresses a different problem than the trailing delete capability described in this document.

## Requirements

- After deletion of an asset blob, there needs to be a period of 30 days during which that blob can be restored.

## Proposed Solution

What we want can be described as a “trailing delete” mechanism. Upon deletion of an asset from the bucket, we would like the object to remain recoverable for some amount of time. S3 already supports this in the form of Bucket Versioning.

### S3 Bucket Versioning

Enabling bucket versioning will change what happens when an object in S3 is deleted. Instead of permanently deleting the object, S3 will simply place a delete marker on it. At that point, the object is hidden from view and appears to be deleted, but still exists and is recoverable.

In addition, we can place an S3 Lifecycle policy on the bucket that automatically clears delete markers and “permanently deletes” their associated objects after some set amount of time.

```
  # Terraform-encoded lifecycle rule.
  # Based on https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-configuration-examples.html#lifecycle-config-conceptual-ex7
  rule {
    id = "ExpireOldDeleteMarkers"
    filter {}

    # Expire objects with delete markers after 30 days
    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    # Also delete any delete markers associated with the expired object
    expiration {
      expired_object_delete_marker = true
    }

    status = "Enabled"
  }
```

This may raise an additional question - since one of the main reasons for this "trailing delete" functionality is to recover from accidental deletion of data, what happens if a delete marker is accidentally deleted? We can solve this by introducing a bucket policy that prevents deletion of delete markers.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PreventDeletionOfDeleteMarkers",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:DeleteObjectVersion",
            "Resource": "arn:aws:s3:::dandi-s3-experiment-bucket/*"
        }
    ]
}
```

In sum: deletion of an asset at the application level will trigger placing a delete marker on the appropriate S3 object; an S3 lifecycle rule will schedule that object for actual deletion 30 days later; an appropriate bucket policy will ensure that nobody can manually destroy data, even by accident. (There is a way to manually destroy data, but it cannot be done by accident: someone with the power to change the bucket policies would first need to remove the protective policy above, and **then** perform a manual delete of the appropriate objects. This affords the right level of security for our purposes: application-level errors will not be able to destroy data irrevocably.)

# Distinction from Data Backup

It’s important to note that the "trailing delete" implementation proposed above does not cover backup of the data in the bucket. While backup is out of scope for this design document, nothing proposed here *prevents* backup from being implemented, and features such as [S3 Replication](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html) may be useful for that.

A possible backup implementation would simply allocate a new bucket in a separate S3 region set to use the Deep Glacier storage tier (to control costs), then use S3 Replication as mentioned above to maintain an object-for-object copy of the production bucket as a pure backup. This backup solution would ***not*** defend against application-level bugs deleting data, but would instead protect the production bucket against larger-scale threats such as destruction of Amazon data centers, etc.
