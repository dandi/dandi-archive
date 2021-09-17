from urllib.parse import urljoin

from django.db import transaction
import djclick as click
import requests

from dandiapi.api.models import Dandiset, Version


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
def import_dandiset_from_response(api_url: str, dandiset_api_response: dict):
    # Check if dandiset with this name already exists. If it does, skip it.
    # I can't think of a better way to uniquely identify dandisets
    # without being able to use identifiers.
    existing_dandiset = Version.objects.filter(name=dandiset_api_response['draft_version']['name'])
    if existing_dandiset.first():
        identifier = existing_dandiset.first().dandiset.identifier
        click.echo(
            f'Skipping {dandiset_api_response["draft_version"]["name"]} - dandiset {identifier} already exists with that name.'  # noqa: E501
        )
        return

    identifier = dandiset_api_response['identifier']
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
        import_dandiset_from_response(api_url, result)

    # Handle API pagination
    if dandiset_api_response.get('next'):
        new_dandisets = requests.get(dandiset_api_response.get('next')).json()
        import_dandisets_from_response(api_url, new_dandisets)


@click.command()
@click.argument('api_url')
def import_dandisets(api_url: str):
    click.echo(f'Importing all dandisets from dandi-api deployment at {api_url}')

    dandisets = requests.get(urljoin(api_url, '/api/dandisets/')).json()
    import_dandisets_from_response(api_url, dandisets)
