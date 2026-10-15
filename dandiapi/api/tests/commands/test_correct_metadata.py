from __future__ import annotations

from copy import deepcopy

import pytest

from dandiapi.api.management.commands.correct_metadata import correct_affiliation_corruption


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
