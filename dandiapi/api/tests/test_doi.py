from __future__ import annotations

from dandischema.conf import get_instance_config
from django.conf import settings
import pytest

from dandiapi.api import doi


@pytest.mark.django_db
def test_generate_doi_data_includes_d3a_related_identifier(published_version):
    doi_value, request_body = doi._generate_doi_data(published_version)
    instance_name = get_instance_config().instance_name.lower()

    assert doi_value == (
        f'{settings.DANDI_DOI_API_PREFIX}/'
        f'{instance_name}.{published_version.dandiset.identifier}/{published_version.version}'
    )
    assert {
        'relatedIdentifier': doi._d3a_metalink_url(published_version),
        'relatedIdentifierType': 'URL',
        'relationType': 'HasMetadata',
        'relatedMetadataScheme': 'Metalink 4.0',
        'schemeURI': 'urn:ietf:params:xml:ns:metalink',
        'schemeType': doi.D3A_METALINK_MEDIA_TYPE,
    } in request_body['data']['attributes']['relatedIdentifiers']


@pytest.mark.django_db
def test_create_doi_registers_d3a_media(mocker, published_version, settings):
    settings.DANDI_DOI_API_URL = 'https://api.example.test/dois'
    settings.DANDI_DOI_API_USER = 'user'
    settings.DANDI_DOI_API_PASSWORD = 'password'

    create_response = mocker.Mock()
    create_response.raise_for_status.return_value = None
    media_response = mocker.Mock()
    media_response.raise_for_status.return_value = None
    post = mocker.patch(
        'dandiapi.api.doi.requests.post', side_effect=[create_response, media_response]
    )

    doi_value = doi.create_doi(published_version)

    assert doi_value == published_version.doi
    assert post.call_args_list[1].args[0] == (
        f'https://api.example.test/dois/{published_version.doi}/media'
    )
    assert post.call_args_list[1].kwargs['json'] == {
        'data': {
            'type': 'media',
            'attributes': {
                'mediaType': doi.D3A_METALINK_MEDIA_TYPE,
                'url': doi._d3a_metalink_url(published_version),
            },
        }
    }
