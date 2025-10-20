from __future__ import annotations

from hashlib import md5
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING
from uuid import uuid4

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

if TYPE_CHECKING:
    from django.contrib.auth.models import User

import djclick as click

from dandiapi.api.asset_paths import add_asset_paths
from dandiapi.api.models import Asset, AssetBlob, Version
from dandiapi.api.models.dandiset import DandisetUserObjectPermission
from dandiapi.api.services.asset import add_asset_to_version
from dandiapi.api.services.metadata import validate_asset_metadata, validate_version_metadata
from dandiapi.api.tasks import calculate_sha256


@click.command()
@click.argument('dandiset_id', required=True)
def create_nwb(dandiset_id: str):
    # Import here so `pynwb` is not a production dependency
    from pynwb import NWBHDF5IO, NWBFile

    draft_version = Version.objects.get(id=dandiset_id)

    dandiset_owner: User = DandisetUserObjectPermission.objects.get(
        content_object=draft_version.dandiset
    ).user

    nwbfile = NWBFile(
        session_description='Mouse exploring an open field',
        identifier='Mouse5_Day3',
        session_start_time=timezone.now(),
        session_id='session_1234',
        experimenter='My Name',
        lab='My Lab Name',
        institution='University of My Institution',
        related_publications='DOI:10.1016/j.neuron.2016.12.011',
    )

    # pynwb API requires file on disk
    with NamedTemporaryFile('rb+', suffix='.nwb') as f:
        with NWBHDF5IO(f.name, mode='w') as io:
            io.write(nwbfile)
        f.seek(0)
        nwb_file = f.read()

    uploaded_file = SimpleUploadedFile(name='test.nwb', content=nwb_file)
    etag = md5(nwb_file).hexdigest() + '-0'  # noqa: S324
    try:
        asset_blob = AssetBlob.objects.get(etag=etag)
    except AssetBlob.DoesNotExist:
        asset_blob = AssetBlob(
            blob_id=uuid4(),
            blob=uploaded_file,
            etag=etag,
            size=uploaded_file.size,
        )
        asset_blob.save()

    asset_metadata = {
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'encodingFormat': 'application/x-nwb',
        'schemaKey': 'Asset',
        'path': 'test.nwb',
    }
    try:
        asset = Asset.objects.get(
            blob=asset_blob,
            metadata=asset_metadata,
        )
        draft_version.assets.add(asset)
        add_asset_paths(asset, draft_version)
    except Asset.DoesNotExist:
        asset = add_asset_to_version(
            user=dandiset_owner,
            version=draft_version,
            asset_blob=asset_blob,
            metadata=asset_metadata,
        )

    calculate_sha256(blob_id=asset_blob.blob_id)
    validate_asset_metadata(asset=asset)
    validate_version_metadata(version=draft_version)

    click.echo(f'Created NWB Asset {asset.id} in dandiset {draft_version.dandiset.identifier}')
