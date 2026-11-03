from __future__ import annotations

from copy import deepcopy

import pytest

from dandiapi.api.services.version.metadata import is_empty_record, strip_empty_records


@pytest.mark.parametrize(
    ('data', 'expected'),
    [
        ({'schemaKey': 'ContactPoint'}, True),
        ({'schemaKey': 'ContactPoint', 'email': None, 'url': ''}, True),
        ({'schemaKey': 'Organization', 'name': '', 'contactPoint': [], 'roleName': []}, True),
        ({'schemaKey': 'EthicsApproval', 'contactPoint': {}}, True),
        ({'schemaKey': 'ContactPoint', 'email': 'a@example.org'}, False),
        # Booleans and numbers carry information, even if they are "falsy"
        ({'schemaKey': 'Organization', 'includeInCitation': False}, False),
        ({'schemaKey': 'QuantitativeValue', 'value': 0}, False),
        # Not records, as they have no schemaKey
        ({}, False),
        ({'email': None}, False),
        (None, False),
        ('ContactPoint', False),
        ([{'schemaKey': 'ContactPoint'}], False),
    ],
)
def test_is_empty_record(data, expected):
    assert is_empty_record(data) is expected


@pytest.mark.parametrize(
    ('metadata', 'expected'),
    [
        pytest.param(
            {'schemaKey': 'Dandiset', 'name': 'foo'},
            {'schemaKey': 'Dandiset', 'name': 'foo'},
            id='nothing-to-strip',
        ),
        pytest.param(
            {'schemaKey': 'Dandiset'},
            {'schemaKey': 'Dandiset'},
            id='top-level-record-is-kept',
        ),
        pytest.param(
            {
                'ethicsApproval': [
                    {
                        'schemaKey': 'EthicsApproval',
                        'identifier': 'IRB-1',
                        'contactPoint': {'schemaKey': 'ContactPoint'},
                    }
                ]
            },
            {'ethicsApproval': [{'schemaKey': 'EthicsApproval', 'identifier': 'IRB-1'}]},
            id='nested-object',
        ),
        pytest.param(
            {
                'contributor': [
                    {
                        'schemaKey': 'Organization',
                        'name': 'Org',
                        'contactPoint': [
                            {'schemaKey': 'ContactPoint'},
                            {'schemaKey': 'ContactPoint', 'email': 'a@example.org'},
                        ],
                    },
                    {
                        'schemaKey': 'Organization',
                        'name': 'Org 2',
                        'contactPoint': [{'schemaKey': 'ContactPoint', 'url': None}],
                    },
                ]
            },
            {
                'contributor': [
                    {
                        'schemaKey': 'Organization',
                        'name': 'Org',
                        'contactPoint': [{'schemaKey': 'ContactPoint', 'email': 'a@example.org'}],
                    },
                    {'schemaKey': 'Organization', 'name': 'Org 2', 'contactPoint': []},
                ]
            },
            id='list-items',
        ),
        pytest.param(
            {
                'ethicsApproval': [
                    {'schemaKey': 'EthicsApproval', 'contactPoint': {'schemaKey': 'ContactPoint'}},
                    {'schemaKey': 'EthicsApproval', 'identifier': 'IRB-2'},
                ]
            },
            {'ethicsApproval': [{'schemaKey': 'EthicsApproval', 'identifier': 'IRB-2'}]},
            id='record-left-empty-is-stripped-too',
        ),
        pytest.param(
            # e.g. the first access item after Version.strip_metadata()
            {'access': [{'contactPoint': {'schemaKey': 'ContactPoint'}}]},
            {'access': [{}]},
            id='objects-without-schemaKey-are-kept',
        ),
        pytest.param(
            {'schemaKey': 'Dandiset', 'keywords': [], 'description': '', 'study': None},
            {'schemaKey': 'Dandiset', 'keywords': [], 'description': '', 'study': None},
            id='blank-values-of-non-empty-records-are-kept',
        ),
    ],
)
def test_strip_empty_records(metadata, expected):
    original = deepcopy(metadata)
    assert strip_empty_records(metadata) == expected
    # The input is not modified
    assert metadata == original
