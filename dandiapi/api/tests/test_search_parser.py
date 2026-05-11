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


def test_contributor_role_ops_match_actual_dandischema_roletype():
    """Guard against schema drift.

    Every non-catch-all `CONTRIBUTOR_ROLE_OPS` value must match a real
    `dandischema.RoleType` member name. Renames or removals on the schema
    side trip this test, forcing an explicit decision here instead of
    silently changing user-facing search syntax.
    """
    from dandischema.models import RoleType

    from dandiapi.api.services.search.operators import CONTRIBUTOR_ROLE_OPS

    role_names = {r.name for r in RoleType}
    for op_name, role_name in CONTRIBUTOR_ROLE_OPS.items():
        if role_name is None:
            continue
        assert role_name in role_names, (
            f'CONTRIBUTOR_ROLE_OPS[{op_name!r}] = {role_name!r} is not a valid '
            'dandischema.RoleType member name'
        )
