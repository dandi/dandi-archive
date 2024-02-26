from __future__ import annotations

import csv
import datetime
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING

import boto3
from django.conf import settings
from django.db import transaction

from dandiapi.api.models import Asset, AssetBlob, Dandiset, Version
from dandiapi.api.services.asset.exceptions import DandisetOwnerRequiredError
from dandiapi.api.storage import get_boto_client

from .exceptions import AssetBlobEmbargoedError, DandisetNotEmbargoedError

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.db.models import QuerySet


def remove_asset_blob_embargoed_tag(asset_blob: AssetBlob) -> None:
    if asset_blob.embargoed:
        raise AssetBlobEmbargoedError

    client = get_boto_client()
    client.delete_object_tagging(
        Bucket=settings.DANDI_DANDISETS_BUCKET_NAME,
        Key=asset_blob.blob.name,
    )


def _upload_dandiset_asset_blobs_manifest(localpath: Path, key: str) -> str:
    """Upload manifest and return ETag."""
    s3_client = get_boto_client()
    with Path.open(localpath, 'rb') as fd:
        resp = s3_client.put_object(Bucket=settings.DANDI_DANDISETS_BUCKET_NAME, Key=key, Body=fd)

    return resp['ETag'].strip('"')


def _remove_dandiset_asset_blob_embargo_tags(dandiset: Dandiset):
    # First we need to generate a CSV manifest containing all asset blobs that need to be untaged
    bucket = settings.DANDI_DANDISETS_BUCKET_NAME
    embargoed_asset_blobs = AssetBlob.objects.filter(
        embargoed=True, assets__versions__dandiset=dandiset
    ).values_list('blob', flat=True)

    # Format timestamp so we get UTC time without timezone info encoded
    timestamp = datetime.datetime.now(tz=datetime.UTC).strftime('%Y-%m-%dT%H:%M:%S')

    # This prefix will be used for both the manifest and job completion report
    batch_job_prefix = f'batch_jobs/{dandiset.identifier}-{timestamp}/'
    blob_manifest_key = f'{batch_job_prefix}manifest.csv'

    # Now we need to upload this CSV manifest so we can point at it from the batch job
    # Using CSV format Bucket,Key
    with tempfile.TemporaryFile(suffix='.csv') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows([(bucket, blob) for blob in embargoed_asset_blobs])

        manifest_etag = _upload_dandiset_asset_blobs_manifest(
            localpath=Path(csvfile.name), key=blob_manifest_key
        )

    # This job will untag all objects listed in the manifest
    batch_client = boto3.client('s3control')
    resp = batch_client.create_job(
        # TODO: Parametrize
        AccountId='278212569472',
        Operation={'S3DeleteObjectTagging': {}},
        Report={
            'Enabled': True,
            'Bucket': bucket,
            'Format': 'Report_CSV_20180820',
            'Prefix': batch_job_prefix,
            'ReportScope': 'FailedTasksOnly',
        },
        Manifest={
            'Spec': {
                'Format': 'S3BatchOperations_CSV_20180820',
                'Fields': ['Bucket', 'Key'],
            },
            'Location': {
                'ObjectArn': f'arn:aws:s3:::{bucket}/{blob_manifest_key}',
                'ETag': manifest_etag,
            },
        },
        # TODO: Parametrize
        RoleArn='arn:aws:iam::278212569472:role/batch-s3-role',
    )
    job_id = resp['JobId']

    # TODO: Wait for this job to finish using the job ID. Then, inspect the generated report to see
    # if there were any failed tasks. If not, continue with the rest of _unembargo_dandiset


@transaction.atomic()
def _unembargo_dandiset(dandiset: Dandiset):
    # NOTE: Before proceeding, all asset blobs must have their embargoed tags removed in s3

    draft_version: Version = dandiset.draft_version
    embargoed_assets: QuerySet[Asset] = draft_version.assets.filter(blob__embargoed=True)
    AssetBlob.objects.filter(assets__in=embargoed_assets).update(embargoed=False)

    # Update draft version metadata
    draft_version.metadata['access'] = [
        {'schemaKey': 'AccessRequirements', 'status': 'dandi:OpenAccess'}
    ]
    draft_version.save()

    # Set access on dandiset
    dandiset.embargo_status = Dandiset.EmbargoStatus.OPEN
    dandiset.save()


def unembargo_dandiset(*, user: User, dandiset: Dandiset):
    """Unembargo a dandiset by copying all embargoed asset blobs to the public bucket."""
    if dandiset.embargo_status != Dandiset.EmbargoStatus.EMBARGOED:
        raise DandisetNotEmbargoedError

    if not user.has_perm('owner', dandiset):
        raise DandisetOwnerRequiredError

    # A scheduled task will pick up any new dandisets with this status and email the admins to
    # initiate the un-embargo process
    dandiset.embargo_status = Dandiset.EmbargoStatus.UNEMBARGOING
    dandiset.save()
