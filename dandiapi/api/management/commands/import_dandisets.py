from urllib.parse import urljoin

from django.db import transaction
import djclick as click
import requests

from dandiapi.api.models import Dandiset, Version
from dandiapi.api.tasks import validate_version_metadata


@transaction.atomic
def import_versions_from_response(api_url: str, version_api_response: dict, dandiset: Dandiset):
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

    # Handle API pagination
    if version_api_response.get('next'):
        next_versions = requests.get(version_api_response.get('next')).json()
        import_versions_from_response(api_url, next_versions, dandiset)


@transaction.atomic
def import_dandiset_from_response(
    api_url: str, dandiset_api_response: dict, should_replace: bool, identifier_offset=0
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

    import_versions_from_response(api_url, versions, dandiset)


@transaction.atomic
def import_dandisets_from_response(
    api_url: str, dandiset_api_response: dict, identifier_offset: int, should_replace: bool
):
    """Import dandisets given a response from /api/dandisets/."""
    for result in dandiset_api_response['results']:
        import_dandiset_from_response(
            api_url, result, identifier_offset=identifier_offset, should_replace=should_replace
        )

    # Handle API pagination
    if dandiset_api_response.get('next'):
        new_dandisets = requests.get(dandiset_api_response.get('next')).json()
        import_dandisets_from_response(api_url, new_dandisets, identifier_offset, should_replace)


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
@click.option('--offset', default=0, help="Offset to add to each new dandiset's identifier.")
@transaction.atomic
def import_dandisets(api_url: str, all: bool, identifier: str, replace: bool, offset=0):
    """Click command to import dandisets from another server deployment."""
    if all:
        click.echo(f'Importing all dandisets from dandi-api deployment at {api_url}')
        dandisets = requests.get(urljoin(api_url, '/api/dandisets/')).json()
        import_dandisets_from_response(api_url, dandisets, offset, should_replace=replace)

    elif identifier:
        click.echo(f'Importing dandiset {identifier} from dandi-api deployment at {api_url}')
        dandiset = requests.get(urljoin(api_url, f'/api/dandisets/{identifier}/')).json()
        import_dandiset_from_response(
            api_url,
            dandiset,
            identifier_offset=offset,
            should_replace=replace,
        )

    else:
        click.echo(
            'Invalid options. Please specify --all or a specific dandiset to import with --identifier.'  # noqa: E501
        )
