from __future__ import annotations

import pytest

from dandiapi.api.services.search.parser import parse_search


def test_empty_string():
    parsed = parse_search('')
    assert parsed.free_text == []
    assert parsed.operators == []


def test_only_free_text():
    parsed = parse_search('hippocampus place cells')
    assert parsed.free_text == ['hippocampus', 'place', 'cells']
    assert parsed.operators == []


def test_only_operators():
    parsed = parse_search('has_species:mouse created_after:2024-01-01')
    assert parsed.free_text == []
    assert parsed.operators == [
        ('has_species', 'mouse'),
        ('created_after', '2024-01-01'),
    ]


def test_mixed():
    parsed = parse_search('place cells has_species:mouse created_after:2024-01-01 ca1')
    assert parsed.free_text == ['place', 'cells', 'ca1']
    assert parsed.operators == [
        ('has_species', 'mouse'),
        ('created_after', '2024-01-01'),
    ]


def test_quoted_phrase_in_free_text():
    parsed = parse_search('"place cells" hippocampus')
    assert parsed.free_text == ['place cells', 'hippocampus']
    assert parsed.operators == []


def test_quoted_operator_value():
    parsed = parse_search('has_technique:"patch clamp"')
    assert parsed.free_text == []
    assert parsed.operators == [('has_technique', 'patch clamp')]


def test_unknown_operator_falls_through_to_free_text():
    parsed = parse_search('foo:bar has_species:mouse')
    assert parsed.free_text == ['foo:bar']
    assert parsed.operators == [('has_species', 'mouse')]


def test_unbalanced_quote_does_not_raise():
    # shlex would raise ValueError; we fall back to plain split.
    parsed = parse_search('hello "world has_species:mouse')
    # In fallback mode, the operator-looking token is still recognized.
    assert ('has_species', 'mouse') in parsed.operators


def test_malformed_date_value_is_kept_in_operators():
    # The parser only tokenizes — date validation happens in the filter layer,
    # which fails closed on malformed dates. Here we just verify the parser
    # treats a malformed value as a normal operator value.
    parsed = parse_search('created_after:not-a-date')
    assert parsed.operators == [('created_after', 'not-a-date')]
    assert parsed.free_text == []


@pytest.mark.parametrize(
    'value',
    ['mouse', 'Mus musculus', 'C57BL/6'],
)
def test_has_species_preserves_value(value):
    parsed = parse_search(f'has_species:"{value}"')
    assert parsed.operators == [('has_species', value)]


def test_repeated_operator_keeps_all():
    parsed = parse_search('has_species:mouse has_species:rat')
    assert parsed.operators == [
        ('has_species', 'mouse'),
        ('has_species', 'rat'),
    ]
