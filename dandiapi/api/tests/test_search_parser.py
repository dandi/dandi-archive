from __future__ import annotations

import pytest

from dandiapi.api.services.search.parser import (
    Operator,
    SearchSyntaxError,
    parse_search,
)

pytestmark = pytest.mark.ai_generated


# Convenience aliases so the parametrize table stays readable.
def _u(key: str, value: str) -> Operator:
    """Unquoted operator (e.g. parsed from `key:value`)."""
    return Operator(key, value, quoted=False)


def _q(key: str, value: str) -> Operator:
    """Quoted operator (e.g. parsed from `key:"value"`)."""
    return Operator(key, value, quoted=True)


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
            'species:mouse created_after:2024-01-01',
            [],
            [_u('species', 'mouse'), _u('created_after', '2024-01-01')],
        ),
        # Mixed
        (
            'place cells species:mouse created_after:2024-01-01 ca1',
            ['place', 'cells', 'ca1'],
            [_u('species', 'mouse'), _u('created_after', '2024-01-01')],
        ),
        # Quoted phrase as free text
        ('"place cells" hippocampus', ['place cells', 'hippocampus'], []),
        # Quoted operator value (multi-word) — `quoted=True`
        ('technique:"patch clamp"', [], [_q('technique', 'patch clamp')]),
        # Repeated operator keeps every entry (AND'd downstream)
        (
            'species:mouse species:rat',
            [],
            [_u('species', 'mouse'), _u('species', 'rat')],
        ),
        # Special characters preserved inside quoted operator value
        ('species:"C57BL/6"', [], [_q('species', 'C57BL/6')]),
        # Quoted token that *looks* like an operator is treated as free text —
        # documented escape hatch for searching for a literal colon.
        ('"foo:bar" hippocampus', ['foo:bar', 'hippocampus'], []),
        # Owner operator (unquoted vs quoted distinguished — used by the
        # `owner:me` magic alias which `owner:"me"` opts out of).
        ('owner:jdoe', [], [_u('owner', 'jdoe')]),
        ('owner:me', [], [_u('owner', 'me')]),
        ('owner:"me"', [], [_q('owner', 'me')]),
        # Owner with email value (the parser doesn't validate the value shape)
        ('owner:user@example.com', [], [_u('owner', 'user@example.com')]),
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
        'owner-username',
        'owner-me-unquoted',
        'owner-me-quoted',
        'owner-email',
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
        ('specie:mouse', 'Did you mean "species"'),
        # Unknown operator (typo) close to a real one
        ('createdafter:2024-01-01', 'Did you mean "created_after"'),
        # Unbalanced quote
        ('hello "world species:mouse', 'Remove the stray quote'),
        ('foo "bar', 'Remove the stray quote'),
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
