from urllib.parse import urljoin
from uuid import uuid4

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
import djclick as click
import requests

from dandiapi.api.models import Asset, AssetBlob, Dandiset, Version, ZarrArchive


@transaction.atomic
def import_assets_from_response(api_url: str, asset_api_response: dict, version: Version):
    uploaded_file = SimpleUploadedFile(name='foo/bar.txt', content=b'A' * 20)
    etag = '76d36e98f312e98ff908c8c82c8dd623-0'
    asset_blob = AssetBlob.objects.get_or_create(
        etag=etag, defaults=dict(blob_id=uuid4(), blob=uploaded_file, etag=etag, size=20)
    )[0]

    for result in asset_api_response['results']:
        blob = result.get('blob')
        zarr = result.get('zarr')

        if blob:
            asset_metadata = {
                'schemaVersion': settings.DANDI_SCHEMA_VERSION,
                'encodingFormat': 'text/plain',
                'schemaKey': 'Asset',
            }
            asset = Asset.objects.create(
                blob=asset_blob, metadata=asset_metadata, path=result['path']
            )
            click.echo(f'    Importing AssetBlob "{asset.path}"')
            version.assets.add(asset)

        elif zarr:
            zarr_info = requests.get(urljoin(api_url, f'/api/zarr/{zarr}/')).json()
            zarr_archive = ZarrArchive.objects.create(
                name=zarr_info['name'],
                dandiset=version.dandiset,
                zarr_id=zarr_info['zarr_id'],
                file_count=zarr_info['file_count'],
                size=zarr_info['size'],
                status=zarr_info['status'],
            )
            asset = Asset.objects.create(zarr=zarr_archive, path=zarr_info['name'])
            click.echo(f'    Importing ZarrArchive "{asset.path}"')
            version.assets.add(asset)

    # Handle API pagination
    if asset_api_response.get('next'):
        next_assets = requests.get(asset_api_response.get('next')).json()
        import_assets_from_response(api_url, next_assets, version)


@transaction.atomic
def import_versions_from_response(
    api_url: str, version_api_response: dict, dandiset: Dandiset, include_assets: bool
):
    """Import versions given a response from /api/dandisets/{identifier}/versions/."""
    for result in version_api_response['results']:
        # get the metadata of this version
        metadata = requests.get(
            urljoin(
                api_url,
                f'/api/dandisets/{result["dandiset"]["identifier"]}/versions/{result["version"]}/',
            )
        ).json()

        click.echo(f'  Importing version "{result["version"]}"')

        version = Version(
            dandiset=dandiset,
            name=result['name'],
            version=result['version'],
            doi=result.get('doi'),
            status=Version.Status.PENDING,
            metadata=metadata,
        )
        version.save()

        if include_assets:
            assets = requests.get(
                urljoin(
                    api_url,
                    f'/api/dandisets/{dandiset.identifier}/versions/{result["version"]}/assets/',
                )
            ).json()
            import_assets_from_response(api_url, assets, version)

    # Handle API pagination
    if version_api_response.get('next'):
        next_versions = requests.get(version_api_response.get('next')).json()
        import_versions_from_response(api_url, next_versions, dandiset)


@transaction.atomic
def import_dandiset_from_response(
    api_url: str,
    dandiset_api_response: dict,
    should_replace: bool,
    include_assets: bool,
    identifier_offset=0,
):
    identifier = dandiset_api_response['identifier']
    new_identifier = int(identifier) + identifier_offset

    dandiset_with_identifier_exists = Dandiset.objects.filter(id=new_identifier).exists()

    # If replacing a dandiset, find the existing one and delete it first
    if dandiset_with_identifier_exists and should_replace:
        Dandiset.objects.get(id=new_identifier).delete()
        dandiset = Dandiset(id=new_identifier)
    elif dandiset_with_identifier_exists:
        click.echo(
            f'Skipping import of dandiset "{new_identifier}": dandiset with that identifier already'
            'exists. Run this script with the --replace flag to enable replacement.'
        )
        return
    else:
        dandiset = Dandiset()

    dandiset.id = new_identifier
    dandiset.save()

    # get all versions associated with this dandiset
    versions = requests.get(urljoin(api_url, f'/api/dandisets/{identifier}/versions/')).json()

    click.echo(
        f'Importing dandiset {identifier} "{dandiset_api_response["draft_version"]["name"]}" as dandiset {dandiset.identifier}'  # noqa: E501
    )

    import_versions_from_response(api_url, versions, dandiset, include_assets)


@transaction.atomic
def import_dandisets_from_response(
    api_url: str,
    dandiset_api_response: dict,
    identifier_offset: int,
    should_replace: bool,
    include_assets: bool,
):
    """Import dandisets given a response from /api/dandisets/."""
    for result in dandiset_api_response['results']:
        import_dandiset_from_response(
            api_url,
            result,
            identifier_offset=identifier_offset,
            should_replace=should_replace,
            include_assets=include_assets,
        )

    # Handle API pagination
    if dandiset_api_response.get('next'):
        new_dandisets = requests.get(dandiset_api_response.get('next')).json()
        import_dandisets_from_response(
            api_url, new_dandisets, identifier_offset, should_replace, include_assets
        )


@click.command()
@click.argument('api_url')
@click.option('--all', is_flag=True, required=False, help='Download all dandisets.')
@click.option('--identifier', required=False, help='The identifier of the dandiset to import.')
@click.option(
    '--replace',
    default=False,
    is_flag=True,
    help='Whether or not to replace an existing dandiset with the same id if it exists',
)
@click.option(
    '--assets',
    default=False,
    is_flag=True,
    help='Whether or not to include Asset records from the dandiset(s).',
)
@click.option('--offset', default=0, help="Offset to add to each new dandiset's identifier.")
@transaction.atomic
def import_dandisets(
    api_url: str, all: bool, identifier: str, replace: bool, assets: bool, offset=0
):
    """Click command to import dandisets from another server deployment."""
    if all:
        click.echo(f'Importing all dandisets from dandi-api deployment at {api_url}')
        dandisets = requests.get(urljoin(api_url, '/api/dandisets/')).json()
        import_dandisets_from_response(
            api_url, dandisets, offset, should_replace=replace, include_assets=assets
        )

    elif identifier:
        click.echo(f'Importing dandiset {identifier} from dandi-api deployment at {api_url}')
        dandiset = requests.get(urljoin(api_url, f'/api/dandisets/{identifier}/')).json()
        import_dandiset_from_response(
            api_url,
            dandiset,
            identifier_offset=offset,
            should_replace=replace,
            include_assets=assets,
        )

    else:
        click.echo(
            'Invalid options. Please specify --all or a specific dandiset to import with --identifier.'  # noqa: E501
        )
