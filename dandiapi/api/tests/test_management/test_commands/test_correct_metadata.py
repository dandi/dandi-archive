from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from dandiapi.api.management.commands.correct_metadata import (
    correct_affiliation_corruption,
    find_objs,
)


@pytest.mark.parametrize(
    ('instance', 'schema_key', 'expected'),
    [
        # Single matching object.
        pytest.param(
            {'schemaKey': 'Test', 'data': 123},
            'Test',
            [{'schemaKey': 'Test', 'data': 123}],
            id='single-match',
        ),
        # No match.
        pytest.param(
            {'schemaKey': 'NotMatch', 'data': 123},
            'Test',
            [],
            id='no-match',
        ),
        # Empty dictionary should return an empty list.
        pytest.param(
            {},
            'Test',
            [],
            id='empty-dict',
        ),
        # Empty list should return an empty list.
        pytest.param(
            [],
            'Test',
            [],
            id='empty-list',
        ),
        # Nested dictionary: the matching object is nested within another dictionary.
        pytest.param(
            {'level1': {'schemaKey': 'Test', 'info': 'nested'}},
            'Test',
            [{'schemaKey': 'Test', 'info': 'nested'}],
            id='nested-dict',
        ),
        # List of dictionaries: only those with matching schema key are returned.
        pytest.param(
            [
                {'schemaKey': 'Test', 'data': 1},
                {'schemaKey': 'Test', 'data': 2},
                {'schemaKey': 'NotTest', 'data': 3},
            ],
            'Test',
            [
                {'schemaKey': 'Test', 'data': 1},
                {'schemaKey': 'Test', 'data': 2},
            ],
            id='list-of-dicts',
        ),
        # Mixed structure: nested dictionaries and lists.
        pytest.param(
            {
                'a': {'schemaKey': 'Test', 'value': 1},
                'b': [
                    {'schemaKey': 'NotTest', 'value': 2},
                    {'schemaKey': 'Test', 'value': 3},
                ],
                'c': 'irrelevant',
                'd': [{'e': {'schemaKey': 'Test', 'value': 4}}],
            },
            'Test',
            [
                {'schemaKey': 'Test', 'value': 1},
                {'schemaKey': 'Test', 'value': 3},
                {'schemaKey': 'Test', 'value': 4},
            ],
            id='mixed-structure',
        ),
        # Non-collection type: integer.
        pytest.param(
            42,
            'Test',
            [],
            id='non-collection-int',
        ),
        # Non-collection type: string.
        pytest.param(
            'some string',
            'Test',
            [],
            id='non-collection-string',
        ),
        # Non-collection type: float.
        pytest.param(
            3.14,
            'Test',
            [],
            id='non-collection-float',
        ),
        # Non-collection type: None.
        pytest.param(
            None,
            'Test',
            [],
            id='non-collection-None',
        ),
        # Nested child: an object with the schema key contains a nested child that also
        # has the schema key.
        pytest.param(
            {'schemaKey': 'Test', 'child': {'schemaKey': 'Test', 'data': 'child'}},
            'Test',
            [
                {'schemaKey': 'Test', 'child': {'schemaKey': 'Test', 'data': 'child'}},
                {'schemaKey': 'Test', 'data': 'child'},
            ],
            id='nested-child',
        ),
        # List in field:
        # The object with the given schema key has a field whose value is a list
        # containing objects, some of which also have the given schema key.
        pytest.param(
            {
                'schemaKey': 'Test',
                'items': [
                    {'schemaKey': 'Test', 'data': 'item1'},
                    {'schemaKey': 'Other', 'data': 'item2'},
                    {'schemaKey': 'Test', 'data': 'item3'},
                ],
            },
            'Test',
            [
                # The outer object is returned first...
                {
                    'schemaKey': 'Test',
                    'items': [
                        {'schemaKey': 'Test', 'data': 'item1'},
                        {'schemaKey': 'Other', 'data': 'item2'},
                        {'schemaKey': 'Test', 'data': 'item3'},
                    ],
                },
                # ...followed by the matching objects within the list.
                {'schemaKey': 'Test', 'data': 'item1'},
                {'schemaKey': 'Test', 'data': 'item3'},
            ],
            id='list-in-field',
        ),
    ],
)
def test_find_objs_parametrized(instance: Any, schema_key: str, expected: list[dict]) -> None:
    result = find_objs(instance, schema_key)
    assert result == expected


@pytest.mark.parametrize(
    ('input_meta', 'expected_output'),
    [
        # No Affiliation object: nothing to change.
        (
            {'key': 'value'},
            None,
        ),
        # Affiliation exists but has no unwanted fields: returns None.
        (
            {'affiliation': {'schemaKey': 'Affiliation', 'name': 'Alice'}},
            None,
        ),
        # Single unwanted field ("contactPoint") should be removed.
        (
            {'affiliation': {'schemaKey': 'Affiliation', 'name': 'Alice', 'contactPoint': 'info'}},
            {'affiliation': {'schemaKey': 'Affiliation', 'name': 'Alice'}},
        ),
        # Multiple unwanted fields should all be removed.
        (
            {
                'affiliation': {
                    'schemaKey': 'Affiliation',
                    'name': 'Test',
                    'contactPoint': 'a',
                    'includeInCitation': 'b',
                    'roleName': 'c',
                }
            },
            {'affiliation': {'schemaKey': 'Affiliation', 'name': 'Test'}},
        ),
        # Nested Affiliation objects should be corrected.
        (
            {
                'users': [
                    {'profile': {'schemaKey': 'Affiliation', 'name': 'Bob', 'roleName': 'Member'}},
                    {'profile': {'schemaKey': 'Affiliation', 'name': 'Charlie'}},
                ],
                'data': {'schemaKey': 'NotAffiliation', 'contactPoint': 'should not be touched'},
            },
            {
                'users': [
                    {'profile': {'schemaKey': 'Affiliation', 'name': 'Bob'}},
                    {'profile': {'schemaKey': 'Affiliation', 'name': 'Charlie'}},
                ],
                'data': {'schemaKey': 'NotAffiliation', 'contactPoint': 'should not be touched'},
            },
        ),
    ],
)
def test_correct_affiliation_corruption(input_meta, expected_output):
    """
    Test `correct_affiliation_corruption()`.

    Ensure that it returns the correct modified metadata (if any corrections are needed)
    while not mutating the original input.
    """
    # Make a deep copy of the input to ensure immutability.
    original_meta = deepcopy(input_meta)
    result = correct_affiliation_corruption(input_meta)

    assert result == expected_output

    # Verify that the original metadata has not been mutated.
    assert input_meta == original_meta, 'The input metadata should remain unchanged.'
