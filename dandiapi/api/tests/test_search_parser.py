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
        # Anatomy values carry their own colons and slashes
        ('anatomy:UBERON:0002421', [], [Operator('anatomy', 'UBERON:0002421')]),
        (
            'anatomy:http://purl.obolibrary.org/obo/UBERON_0002421',
            [],
            [Operator('anatomy', 'http://purl.obolibrary.org/obo/UBERON_0002421')],
        ),
        (
            'anatomy_exact:"CA1 field" species:mouse',
            [],
            [Operator('anatomy_exact', 'CA1 field'), Operator('species', 'mouse')],
        ),
        # A pasted URL is free text, as is an uppercase CURIE
        (
            'https://purl.brain-bican.org/ontology/mbao/MBA_1089 UBERON:0002421',
            ['https://purl.brain-bican.org/ontology/mbao/MBA_1089', 'UBERON:0002421'],
            [],
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
        # Quoted token that *looks* like an operator is treated as free text —
        # documented escape hatch for searching for a literal colon.
        ('"foo:bar" hippocampus', ['foo:bar', 'hippocampus'], []),
        # Owner operator
        ('owner:jdoe', [], [Operator('owner', 'jdoe')]),
        ('owner:user@example.com', [], [Operator('owner', 'user@example.com')]),
    ],
    ids=[
        'empty',
        'whitespace-only',
        'free-text-only',
        'operators-only',
        'anatomy-curie-value',
        'anatomy-url-value',
        'anatomy-exact-quoted-value',
        'bare-url-and-uppercase-curie-are-free-text',
        'mixed-operators-and-free-text',
        'quoted-phrase-free-text',
        'quoted-operator-value',
        'repeated-operator-key',
        'special-chars-in-quoted-value',
        'quoted-operator-like-token-is-free-text',
        'owner-username',
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


@pytest.mark.parametrize(
    ('query', 'suggestion'),
    [
        ('uberon:0002421', 'anatomy:UBERON:0002421'),
        ('mba:1089', 'anatomy:MBA:1089'),
    ],
)
def test_bare_lowercase_curie_suggests_the_anatomy_operator(query, suggestion):
    with pytest.raises(SearchSyntaxError, match=suggestion):
        parse_search(query)
