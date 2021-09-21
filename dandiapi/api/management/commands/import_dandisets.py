from urllib.parse import urljoin

from django.db import connection, transaction
from django.db.utils import OperationalError
import djclick as click
import requests

from dandiapi.api.models import Dandiset, Version
from dandiapi.api.tasks import validate_version_metadata


@transaction.atomic
def set_sequence_value(new_value: int):
    """Set api_dandiset_id_seq value."""
    cursor = connection.cursor()
    cursor.execute(f'ALTER SEQUENCE api_dandiset_id_seq RESTART WITH {new_value}')


@transaction.atomic
def get_sequence_value():
    """Get current api_dandiset_id_seq value."""
    cursor = connection.cursor()
    try:
        cursor.execute('SELECT last_value FROM api_dandiset_id_seq')
    except OperationalError:
        cursor.execute('CREATE SEQUENCE api_dandiset_id_seq START 1')
        cursor.execute('SELECT last_value FROM api_dandiset_id_seq')
    return cursor.fetchone()[0]


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
            status=result['status'],
            metadata=metadata,
        )
        version.save()

    # Handle API pagination
    if version_api_response.get('next'):
        next_versions = requests.get(version_api_response.get('next')).json()
        import_versions_from_response(api_url, next_versions, dandiset)


@transaction.atomic
def import_dandiset_from_response(
    api_url: str,
    dandiset_api_response: dict,
    dandiset_to_replace=None,
    skip_existing_names=True,
):
    if skip_existing_names:
        # Check if dandiset with this name already exists. If it does, skip it.
        # I can't think of a better way to uniquely identify dandisets
        # without being able to use identifiers.
        existing_dandiset = Version.objects.filter(
            name=dandiset_api_response['draft_version']['name']
        )
        if existing_dandiset.exists():
            identifier = existing_dandiset.first().dandiset.identifier
            click.echo(
                f'Skipping {dandiset_api_response["draft_version"]["name"]} - dandiset {identifier} already exists with that name.'  # noqa: E501
            )
            return

    identifier = dandiset_api_response['identifier']

    # If replacing a dandiset, find the existing one and delete it first
    if dandiset_to_replace is not None:
        Dandiset.objects.get(id=dandiset_to_replace).delete()
        dandiset = Dandiset(id=dandiset_to_replace)
    else:
        dandiset = Dandiset()

    dandiset.save()

    # get all versions associated with this dandiset
    versions = requests.get(urljoin(api_url, f'/api/dandisets/{identifier}/versions/')).json()

    click.echo(
        f'Importing dandiset {identifier} "{dandiset_api_response["draft_version"]["name"]}" as dandiset {dandiset.identifier}'  # noqa: E501
    )

    import_versions_from_response(api_url, versions, dandiset)


@transaction.atomic
def import_dandisets_from_response(api_url: str, dandiset_api_response: dict):
    """Import dandisets given a response from /api/dandisets/."""
    for result in dandiset_api_response['results']:
        import_dandiset_from_response(api_url, result, skip_existing_names=False)

    # Handle API pagination
    if dandiset_api_response.get('next'):
        new_dandisets = requests.get(dandiset_api_response.get('next')).json()
        import_dandisets_from_response(
            api_url,
            new_dandisets,
        )


@click.command()
@click.argument('api_url')
@click.option('--all', is_flag=True, required=False, help='Download all dandisets.')
@click.option('--identifier', required=False, help='The identifier of the dandiset to import.')
@click.option('--replace', default=None, help='The dandiset to replace with the imported one.')
@click.option('--offset', default=0, help="Offset to add to each new dandiset's identifier.")
@transaction.atomic
def import_dandisets(api_url: str, all: bool, identifier: str, replace: str, offset=0):
    original_sequence_value = get_sequence_value()
    set_sequence_value(original_sequence_value + offset)
    if all:
        click.echo(f'Importing all dandisets from dandi-api deployment at {api_url}')
        dandisets = requests.get(urljoin(api_url, '/api/dandisets/')).json()
        import_dandisets_from_response(api_url, dandisets)
        set_sequence_value(original_sequence_value)

    elif identifier:
        click.echo(f'Importing dandiset {identifier} from dandi-api deployment at {api_url}')
        dandiset = requests.get(urljoin(api_url, f'/api/dandisets/{identifier}/')).json()
        import_dandiset_from_response(
            api_url,
            dandiset,
            dandiset_to_replace=replace,
            skip_existing_names=False,
        )
        set_sequence_value(original_sequence_value)

    else:
        click.echo(
            'Invalid options. Please specify --all or a specific dandiset to import with --identifier.'  # noqa: E501
        )
