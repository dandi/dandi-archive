from __future__ import annotations

from copy import deepcopy

import pytest

from dandiapi.api.services.version.metadata import strip_empty_records

EMPTY = {'schemaKey': 'ContactPoint'}
FILLED = {'schemaKey': 'ContactPoint', 'email': 'a@example.org'}


@pytest.mark.parametrize(
    ('metadata', 'expected'),
    [
        pytest.param(
            {'schemaKey': 'Dandiset', 'keywords': [], 'description': ''},
            {'schemaKey': 'Dandiset', 'keywords': [], 'description': ''},
            id='nothing-to-strip',
        ),
        pytest.param({'schemaKey': 'Dandiset'}, {'schemaKey': 'Dandiset'}, id='top-level-kept'),
        pytest.param(
            {'ethicsApproval': [{'identifier': 'IRB-1', 'contactPoint': EMPTY}]},
            {'ethicsApproval': [{'identifier': 'IRB-1'}]},
            id='nested-object',
        ),
        pytest.param(
            {'contactPoint': [EMPTY, FILLED], 'roleName': [EMPTY]},
            {'contactPoint': [FILLED], 'roleName': []},
            id='list-items',
        ),
        pytest.param(
            {'ethicsApproval': [{'schemaKey': 'EthicsApproval', 'contactPoint': EMPTY}]},
            {'ethicsApproval': []},
            id='record-left-empty',
        ),
        pytest.param(
            # Falsy values carry information too
            {'contributor': [{'schemaKey': 'Person', 'includeInCitation': False}]},
            {'contributor': [{'schemaKey': 'Person', 'includeInCitation': False}]},
            id='falsy-values-kept',
        ),
    ],
)
def test_strip_empty_records(metadata, expected):
    original = deepcopy(metadata)
    assert strip_empty_records(metadata) == expected
    assert metadata == original
