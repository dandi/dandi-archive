# S3 Object Lock Legal Holds


## Terminology
The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

## Why make published blobs immutable?

The DANDI Archive's core value proposition is hosting reliable, citable scientific data. Once a dandiset is published and assigned a DOI, the data it references MUST remain immutable to preserve the integrity of scientific citations and reproducibility. Users who cite a published dandiset expect that the data will remain exactly as it was at the time of publication.

Currently, while our application logic prevents modification of published assets, there is no infrastructure-level enforcement.  Adding S3-level immutability provides stronger data safety.

## Requirements

- Published asset blobs MUST be immutable at the S3 infrastructure level
- The immutability mechanism MUST not interfere with the existing trailing delete functionality (S3 Bucket Versioning)
- The solution MUST be compatible with future garbage collection features
- The mechanism SHOULD be efficient when applied to large numbers of blobs during publication
- There MUST be some sort of "backdoor" that allows deletion of published blobs if necessary, in case of extreme circumstances that warrant deletion of a published asset and/or dandiset

## Proposed Solution

AWS S3 Object Lock with legal holds provides exactly the protection we need. A legal hold is a flag that can be applied to an S3 object version to prevent deletion or modification, regardless of any retention policies or IAM permissions. Unlike retention modes, legal holds have no expiration date and remain in effect until explicitly removed via the `s3:PutObjectLegalHold` S3 API. See the [documentation for S3 legal holds](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html#object-lock-legal-holds) for more details.

### S3 Object Lock

S3 Object Lock is a feature that prevents object versions from being deleted or overwritten for a specified period or indefinitely. It operates in three ways:

1. **Governance mode**: Prevents most users from deleting object versions, but users with special permissions can override
2. **Compliance mode**: No user can delete the object version until the retention period expires, including the root account
3. **Legal hold**: A separate flag independent of retention mode that prevents deletion until removed

Goverence and compliance modes operate at the bucket level, while legal holds operate at the object level.

For our use case, **legal holds** are the appropriate choice because:
- Only published assets need protection from deletion, other objects in the bucket MUST remain deletable
- Published assets MUST remain immutable permanently (no expiration)
- There MUST be the ability to remove the hold if absolutely necessary (per the "backdoor" requirement)
- Legal holds are independent of retention policies and work alongside bucket versioning

## Interaction with Garbage Collection

Legal holds MUST NOT interfere with garbage collection of unpublished assets, as only published asset blobs SHALL have legal holds applied. The garbage collection processes for orphaned uploads, unreferenced AssetBlobs, and unpublished assets MUST continue to work as designed.
Any violation of this, i.e. any interference, as e.g. attempt to remove a blob which is under Legal hold MUST be considered to be a bug as MUST NOT happen under current design, and thus will not be silently ignored. 

### Potential Interference Scenarios (and Why They Don't Occur)

The following scenarios could theoretically interfere with garbage collection, but do NOT occur with this design:

1. **Overly broad legal holds**: If legal holds were accidentally applied to unpublished blobs, those blobs could not be deleted by garbage collection processes until the holds were manually removed.
1. **Bucket-wide retention policies**: If we used compliance or governance mode at the bucket level, ALL objects (including unpublished assets, orphaned uploads, and manifest files, etc.) would be protected from deletion for the retention period. This would prevent garbage collection processes from cleaning up:
   - Abandoned multipart uploads
   - Orphaned asset blobs
   - Old manifest file versions

**Why legal holds avoid these issues:**
- Unpublished assets never receive legal holds, so they remain fully deletable while the deletion permissions remain intact for object versions without legal holds
- Legal holds are applied at the **object level**, only to specific published asset blobs. i.e., they are **object-level retention policies** instead of **bucket-wide retention policies**.

## Cost Considerations

- S3 Object Lock has no additional per-request or storage costs
- Legal holds are metadata flags with no storage overhead

## Rollout Plan

Note: this SHOULD be done on the sandbox deployment first, then the production deployment.

1. Enable S3 Object Lock on the bucket
2. Deploy code changes to apply legal holds during publish celery task
3. Run a one-time script to apply legal holds to all existing published asset blobs

## Alternative Approach Considered

### Bucket Policy with Object Tagging

An appealing approach might be to tag published blobs with a `published=true` tag and use a bucket policy to deny `s3:DeleteObject` for objects with that tag. This is similar to how we deny access (i.e. `s3:GetObject`) permissions to embargoed blobs (see Embargo Redesign doc for more info). However, this approach **cannot be used** due to an AWS limitation.

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
