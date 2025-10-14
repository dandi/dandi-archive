# S3 Object Lock Legal Holds

## Why make published blobs immutable?

The DANDI Archive's core value proposition is hosting reliable, citable scientific data. Once a dandiset is published and assigned a DOI, the data it references must remain immutable to preserve the integrity of scientific citations and reproducibility. Users who cite a published dandiset expect that the data will remain exactly as it was at the time of publication.

Currently, while our application logic prevents modification of published assets, there is no infrastructure-level enforcement.  Adding S3-level immutability provides stronger data safety.

## Requirements

- Published asset blobs must be immutable at the S3 infrastructure level
- The immutability mechanism should not interfere with the existing trailing delete functionality (S3 Bucket Versioning)
- The solution should be compatible with future garbage collection features
- The mechanism should be efficient when applied to large numbers of blobs during publication
- There should be some sort of "backdoor" that allows deletion of published blobs if necessary, in case of extreme circumstances that warrant deletion of a published asset and/or dandiset

## Proposed Solution

AWS S3 Object Lock with legal holds provides exactly the protection we need. A legal hold is a flag that can be applied to an S3 object to prevent deletion or modification, regardless of any retention policies or IAM permissions. Unlike retention modes, legal holds have no expiration date and remain in effect until explicitly removed via the `s3:PutObjectLegalHold` S3 API. See the [documentation for S3 legal holds](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html#object-lock-legal-holds) for more details.

### S3 Object Lock

S3 Object Lock is a feature that prevents objects from being deleted or overwritten for a specified period or indefinitely. It operates in three ways:

1. **Governance mode**: Prevents most users from deleting objects, but users with special permissions can override
2. **Compliance mode**: No user can delete the object until the retention period expires, including the root account
3. **Legal hold**: A separate flag independent of retention mode that prevents deletion until removed

Goverence and compliance modes operate at the bucket level, while legal holds operate at the object level.

For our use case, **legal holds** are the appropriate choice because:
- We only want to prevent deletion of published assets, other objects in the bucket should remain deletable
- Published assets should remain immutable permanently (no expiration)
- We still want the ability to remove the hold if absolutely necessary
- Legal holds are independent of retention policies and work alongside bucket versioning

## Interaction with Garbage Collection

Legal holds do not interfere with garbage collection of unpublished assets, as only published asset blobs will have legal holds applied. The garbage collection processes for orphaned uploads, unreferenced AssetBlobs, and unpublished assets will continue to work as designed.

## Cost Considerations

- S3 Object Lock has no additional per-request or storage costs
- Legal holds are metadata flags with no storage overhead

## Rollout Plan

Note: this should be done on the sandbox deployment first, then the production deployment.

1. Enable S3 Object Lock on the bucket
2. Deploy code changes to apply legal holds during publish celery task
3. Run a one-time script to apply legal holds to all existing published asset blobs

## Alternative Approach Considered

### Bucket Policy with Object Tagging

An appealing approach might be to tag published blobs with a `published=true` tag and use a bucket policy to deny `s3:DeleteObject` for objects with that tag. This is similar to how we deny access (i.e. `s3:GetObject`) permissions to embargoed blobs (see Embargo Redesign doc for more info). However, this approach **does not work** due to an AWS limitation.

The `s3:DeleteObject` action does not support the `s3:ExistingObjectTag/<tag_name>` condition key, according to [AWS documentation](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazons3.html#amazons3-actions-as-permissions).

This means you cannot write a bucket policy like:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:DeleteObject",
      "Resource": "arn:aws:s3:::dandi-dandisets-bucket/*",
      "Condition": {
        "StringEquals": {
          "s3:ExistingObjectTag/published": "true"
        }
      }
    }
  ]
}
```

This is a fundamental limitation of S3's support for delete operations, which makes S3 Object Lock legal holds the correct solution for protecting specific objects based on their published state.
