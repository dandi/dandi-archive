from __future__ import annotations

import pytest

from dandiapi.api.services.search.parser import (
    SearchSyntaxError,
    parse_search,
)

pytestmark = pytest.mark.ai_generated


@pytest.mark.parametrize(
    ('query', 'expected_free_text', 'expected_operators'),
    [
        # Empty / whitespace
        ('', [], []),
        ('   ', [], []),
        # Free text only
        ('hippocampus place cells', ['hippocampus', 'place', 'cells'], []),
        # Operators only
        (
            'has_species:mouse created_after:2024-01-01',
            [],
            [('has_species', 'mouse'), ('created_after', '2024-01-01')],
        ),
        # Mixed
        (
            'place cells has_species:mouse created_after:2024-01-01 ca1',
            ['place', 'cells', 'ca1'],
            [('has_species', 'mouse'), ('created_after', '2024-01-01')],
        ),
        # Quoted phrase as free text
        ('"place cells" hippocampus', ['place cells', 'hippocampus'], []),
        # Quoted operator value (multi-word)
        ('has_technique:"patch clamp"', [], [('has_technique', 'patch clamp')]),
        # Repeated operator keeps every entry (AND'd downstream)
        (
            'has_species:mouse has_species:rat',
            [],
            [('has_species', 'mouse'), ('has_species', 'rat')],
        ),
        # Special characters preserved inside quoted operator value
        ('has_species:"C57BL/6"', [], [('has_species', 'C57BL/6')]),
        # Quoted token that *looks* like an operator is treated as free text —
        # this is the documented escape hatch for searching for a literal colon.
        ('"foo:bar" hippocampus', ['foo:bar', 'hippocampus'], []),
    ],
    ids=[
        'empty',
        'whitespace-only',
        'free-text-only',
        'operators-only',
        'mixed-operators-and-free-text',
        'quoted-phrase-free-text',
        'quoted-operator-value',
        'repeated-operator-key',
        'special-chars-in-quoted-value',
        'quoted-operator-like-token-is-free-text',
    ],
)
def test_parse_search(query, expected_free_text, expected_operators):
    parsed = parse_search(query)
    assert parsed.free_text == expected_free_text
    assert parsed.operators == expected_operators


@pytest.mark.parametrize(
    ('query', 'expected_message_fragment'),
    [
        # Unknown operator — generic
        ('foo:bar', 'Unknown search operator "foo"'),
        # Unknown operator close to a real one — should suggest
        ('has_specie:mouse', 'Did you mean "has_species"'),
        # Unknown operator (typo) close to a real one
        ('createdafter:2024-01-01', 'Did you mean "created_after"'),
        # Unbalanced quote
        ('hello "world has_species:mouse', 'Unbalanced quote'),
        ('foo "bar', 'Unbalanced quote'),
        # Length cap (DoS hardening)
        ('a' * 5000, 'too long'),
    ],
    ids=[
        'unknown-operator-no-suggestion',
        'unknown-operator-typo-suggests',
        'unknown-operator-missing-underscore-suggests',
        'unbalanced-quote-mid-string',
        'unbalanced-quote-trailing',
        'over-length-cap',
    ],
)
def test_parse_search_raises_on_invalid_query(query, expected_message_fragment):
    with pytest.raises(SearchSyntaxError, match=expected_message_fragment):
        parse_search(query)
