from __future__ import annotations

import pytest

from dandiapi.api.services.search.parser import (
    Operator,
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
            'species:mouse created_after:2024-01-01',
            [],
            [Operator('species', 'mouse'), Operator('created_after', '2024-01-01')],
        ),
        # Mixed
        (
            'place cells species:mouse created_after:2024-01-01 ca1',
            ['place', 'cells', 'ca1'],
            [Operator('species', 'mouse'), Operator('created_after', '2024-01-01')],
        ),
        # Quoted phrase as free text
        ('"place cells" hippocampus', ['place cells', 'hippocampus'], []),
        # Quoted operator value (multi-word)
        ('technique:"patch clamp"', [], [Operator('technique', 'patch clamp')]),
        # Repeated operator keeps every entry (AND'd downstream)
        (
            'species:mouse species:rat',
            [],
            [Operator('species', 'mouse'), Operator('species', 'rat')],
        ),
        # Special characters preserved inside quoted operator value
        ('species:"C57BL/6"', [], [Operator('species', 'C57BL/6')]),
        # Data-standard operator
        ('standard:nwb', [], [Operator('standard', 'nwb')]),
        # Measured-variable operator
        ('variable:LFP', [], [Operator('variable', 'LFP')]),
        # Quoted token that *looks* like an operator is treated as free text —
        # documented escape hatch for searching for a literal colon.
        ('"foo:bar" hippocampus', ['foo:bar', 'hippocampus'], []),
        # Owner operator
        ('owner:jdoe', [], [Operator('owner', 'jdoe')]),
        ('owner:user@example.com', [], [Operator('owner', 'user@example.com')]),
        # A key with no value is free text, not an operator
        ('species: mouse', ['species:', 'mouse'], []),
        # Keys are lowercase; anything else is free text
        ('Species:mouse', ['Species:mouse'], []),
        # Only the first colon separates key from value
        ('owner:a:b', [], [Operator('owner', 'a:b')]),
        # Tabs and repeated spaces separate terms like a single space
        ('mouse\t  species:rat', ['mouse'], [Operator('species', 'rat')]),
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
        'standard-operator',
        'variable-operator',
        'quoted-operator-like-token-is-free-text',
        'owner-username',
        'owner-email',
        'key-without-value-is-free-text',
        'uppercase-key-is-free-text',
        'value-keeps-later-colons',
        'mixed-whitespace',
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
        # Empty or whitespace-only operator value
        ('species:""', 'requires a value'),
        ('species:"  "', 'requires a value'),
        # Malformed date
        ('created_after:yesterday', 'Invalid date for "created_after"'),
        # Terms are validated in order: the first bad term is reported
        ('created_after:yesterday specie:mouse', 'Invalid date'),
        ('specie:mouse created_after:yesterday', 'Did you mean "species"'),
    ],
    ids=[
        'unknown-operator-no-suggestion',
        'unknown-operator-typo-suggests',
        'unknown-operator-missing-underscore-suggests',
        'unbalanced-quote-mid-string',
        'unbalanced-quote-trailing',
        'over-length-cap',
        'empty-operator-value',
        'blank-operator-value',
        'malformed-date',
        'first-bad-term-wins-date',
        'first-bad-term-wins-key',
    ],
)
def test_parse_search_raises_on_invalid_query(query, expected_message_fragment):
    with pytest.raises(SearchSyntaxError, match=expected_message_fragment):
        parse_search(query)
