from __future__ import annotations

import pytest
from django.db.models import Q

from dandiapi.api.views.dandiset import SearchParser


class TestSearchParser:
    """Comprehensive tests for the SearchParser class."""

    # Basic word parsing tests
    def test_single_word(self):
        """Test parsing a single word."""
        parser = SearchParser('neuron')
        result = parser.parse()
        expected = Q(search_field__icontains='neuron')
        assert str(result) == str(expected)

    def test_multiple_words_implicit_and(self):
        """Test that multiple words are implicitly AND'ed together."""
        parser = SearchParser('neural mouse cortex')
        result = parser.parse()
        expected = (
            Q(search_field__icontains='neural')
            & Q(search_field__icontains='mouse')
            & Q(search_field__icontains='cortex')
        )
        assert str(result) == str(expected)

    def test_empty_string(self):
        """Test parsing an empty string returns empty Q object."""
        parser = SearchParser('')
        result = parser.parse()
        assert str(result) == str(Q())

    def test_whitespace_only(self):
        """Test parsing whitespace-only string returns empty Q object."""
        parser = SearchParser('   ')
        result = parser.parse()
        assert str(result) == str(Q())

    # Quoted phrase tests
    def test_quoted_phrase(self):
        """Test parsing a quoted phrase."""
        parser = SearchParser('"neural activity"')
        result = parser.parse()
        expected = Q(search_field__icontains='neural activity')
        assert str(result) == str(expected)

    def test_quoted_phrase_with_spaces(self):
        """Test quoted phrase with multiple spaces preserved."""
        parser = SearchParser('"neural   activity   patterns"')
        result = parser.parse()
        expected = Q(search_field__icontains='neural   activity   patterns')
        assert str(result) == str(expected)

    def test_unclosed_quote(self):
        """Test that unclosed quotes still parse correctly."""
        parser = SearchParser('"neural activity')
        result = parser.parse()
        # Should treat the rest of the string as the quoted content
        expected = Q(search_field__icontains='neural activity')
        assert str(result) == str(expected)

    def test_empty_quotes(self):
        """Test empty quoted string."""
        parser = SearchParser('""')
        result = parser.parse()
        expected = Q(search_field__icontains='')
        assert str(result) == str(expected)

    def test_quoted_phrase_and_word(self):
        """Test combination of quoted phrase and regular word."""
        parser = SearchParser('"neural activity" mouse')
        result = parser.parse()
        expected = Q(search_field__icontains='neural activity') & Q(search_field__icontains='mouse')
        assert str(result) == str(expected)

    # AND operator tests
    def test_explicit_and_operator(self):
        """Test explicit AND operator."""
        parser = SearchParser('neural AND mouse')
        result = parser.parse()
        expected = Q(search_field__icontains='neural') & Q(search_field__icontains='mouse')
        assert str(result) == str(expected)

    def test_multiple_and_operators(self):
        """Test multiple AND operators."""
        parser = SearchParser('neural AND mouse AND cortex')
        result = parser.parse()
        expected = (
            Q(search_field__icontains='neural')
            & Q(search_field__icontains='mouse')
            & Q(search_field__icontains='cortex')
        )
        assert str(result) == str(expected)

    def test_and_operator_case_sensitive(self):
        """Test that AND must be uppercase."""
        parser = SearchParser('neural and mouse')
        result = parser.parse()
        # 'and' should be treated as a regular word
        expected = (
            Q(search_field__icontains='neural')
            & Q(search_field__icontains='and')
            & Q(search_field__icontains='mouse')
        )
        assert str(result) == str(expected)

    # OR operator tests
    def test_or_operator(self):
        """Test OR operator."""
        parser = SearchParser('neural OR mouse')
        result = parser.parse()
        expected = Q(search_field__icontains='neural') | Q(search_field__icontains='mouse')
        assert str(result) == str(expected)

    def test_multiple_or_operators(self):
        """Test multiple OR operators."""
        parser = SearchParser('neural OR mouse OR cortex')
        result = parser.parse()
        expected = (
            Q(search_field__icontains='neural')
            | Q(search_field__icontains='mouse')
            | Q(search_field__icontains='cortex')
        )
        assert str(result) == str(expected)

    def test_or_operator_case_sensitive(self):
        """Test that OR must be uppercase."""
        parser = SearchParser('neural or mouse')
        result = parser.parse()
        # 'or' should be treated as a regular word
        expected = (
            Q(search_field__icontains='neural')
            & Q(search_field__icontains='or')
            & Q(search_field__icontains='mouse')
        )
        assert str(result) == str(expected)

    # NOT operator tests
    def test_not_operator(self):
        """Test NOT operator."""
        parser = SearchParser('NOT neural')
        result = parser.parse()
        expected = ~Q(search_field__icontains='neural')
        assert str(result) == str(expected)

    def test_not_with_and(self):
        """Test NOT combined with AND."""
        parser = SearchParser('neural AND NOT mouse')
        result = parser.parse()
        expected = Q(search_field__icontains='neural') & ~Q(search_field__icontains='mouse')
        assert str(result) == str(expected)

    def test_not_with_or(self):
        """Test NOT combined with OR."""
        parser = SearchParser('neural OR NOT mouse')
        result = parser.parse()
        expected = Q(search_field__icontains='neural') | ~Q(search_field__icontains='mouse')
        assert str(result) == str(expected)

    def test_multiple_not_operators(self):
        """Test multiple NOT operators."""
        parser = SearchParser('NOT neural NOT mouse')
        result = parser.parse()
        expected = ~Q(search_field__icontains='neural') & ~Q(search_field__icontains='mouse')
        assert str(result) == str(expected)

    def test_not_operator_case_sensitive(self):
        """Test that NOT must be uppercase."""
        parser = SearchParser('not neural')
        result = parser.parse()
        # 'not' should be treated as a regular word
        expected = Q(search_field__icontains='not') & Q(search_field__icontains='neural')
        assert str(result) == str(expected)

    # Parentheses tests
    def test_simple_parentheses(self):
        """Test simple parentheses grouping."""
        parser = SearchParser('(neural)')
        result = parser.parse()
        expected = Q(search_field__icontains='neural')
        assert str(result) == str(expected)

    def test_parentheses_with_or(self):
        """Test parentheses with OR operator."""
        parser = SearchParser('(neural OR mouse)')
        result = parser.parse()
        expected = Q(search_field__icontains='neural') | Q(search_field__icontains='mouse')
        assert str(result) == str(expected)

    def test_parentheses_with_and_or_precedence(self):
        """Test that parentheses control precedence of AND and OR."""
        parser = SearchParser('(neural OR mouse) AND cortex')
        result = parser.parse()
        expected = (Q(search_field__icontains='neural') | Q(search_field__icontains='mouse')) & Q(
            search_field__icontains='cortex'
        )
        assert str(result) == str(expected)

    def test_nested_parentheses(self):
        """Test nested parentheses."""
        parser = SearchParser('((neural OR mouse) AND cortex)')
        result = parser.parse()
        expected = (Q(search_field__icontains='neural') | Q(search_field__icontains='mouse')) & Q(
            search_field__icontains='cortex'
        )
        assert str(result) == str(expected)

    def test_multiple_parenthesis_groups(self):
        """Test multiple parenthesis groups."""
        parser = SearchParser('(neural OR mouse) AND (cortex OR brain)')
        result = parser.parse()
        expected = (Q(search_field__icontains='neural') | Q(search_field__icontains='mouse')) & (
            Q(search_field__icontains='cortex') | Q(search_field__icontains='brain')
        )
        assert str(result) == str(expected)

    def test_unclosed_parenthesis(self):
        """Test unclosed parenthesis."""
        parser = SearchParser('(neural OR mouse')
        result = parser.parse()
        # Should still parse the content inside
        expected = Q(search_field__icontains='neural') | Q(search_field__icontains='mouse')
        assert str(result) == str(expected)

    def test_empty_parentheses(self):
        """Test empty parentheses."""
        parser = SearchParser('()')
        result = parser.parse()
        # Empty parentheses should return empty Q object
        assert str(result) == str(Q())

    # Complex expression tests
    def test_complex_expression_1(self):
        """Test complex expression: (A OR B) AND (C OR D)."""
        parser = SearchParser('(neural OR mouse) AND (cortex OR brain)')
        result = parser.parse()
        expected = (Q(search_field__icontains='neural') | Q(search_field__icontains='mouse')) & (
            Q(search_field__icontains='cortex') | Q(search_field__icontains='brain')
        )
        assert str(result) == str(expected)

    def test_complex_expression_2(self):
        """Test complex expression: A AND (B OR C) AND NOT D."""
        parser = SearchParser('neural AND (mouse OR rat) AND NOT elephant')
        result = parser.parse()
        expected = (
            Q(search_field__icontains='neural')
            & (Q(search_field__icontains='mouse') | Q(search_field__icontains='rat'))
            & ~Q(search_field__icontains='elephant')
        )
        assert str(result) == str(expected)

    def test_complex_expression_3(self):
        """Test complex expression with quoted phrases."""
        parser = SearchParser('"neural activity" AND (mouse OR rat)')
        result = parser.parse()
        expected = Q(search_field__icontains='neural activity') & (
            Q(search_field__icontains='mouse') | Q(search_field__icontains='rat')
        )
        assert str(result) == str(expected)

    def test_complex_expression_4(self):
        """Test complex expression: NOT (A OR B)."""
        parser = SearchParser('NOT (neural OR mouse)')
        result = parser.parse()
        expected = ~(Q(search_field__icontains='neural') | Q(search_field__icontains='mouse'))
        assert str(result) == str(expected)

    def test_complex_expression_5(self):
        """Test complex expression with multiple levels."""
        parser = SearchParser('(A OR B) AND (C OR (D AND E))')
        result = parser.parse()
        expected = (Q(search_field__icontains='A') | Q(search_field__icontains='B')) & (
            Q(search_field__icontains='C')
            | (Q(search_field__icontains='D') & Q(search_field__icontains='E'))
        )
        assert str(result) == str(expected)

    # Operator precedence tests
    def test_precedence_and_before_or(self):
        """Test that AND has higher precedence than OR: A OR B AND C = A OR (B AND C)."""
        parser = SearchParser('A OR B AND C')
        result = parser.parse()
        # Due to the parser's structure, it will parse as: A OR (B AND C)
        expected = Q(search_field__icontains='A') | (
            Q(search_field__icontains='B') & Q(search_field__icontains='C')
        )
        assert str(result) == str(expected)

    def test_precedence_not_highest(self):
        """Test that NOT has highest precedence."""
        parser = SearchParser('A AND NOT B OR C')
        result = parser.parse()
        # Should parse as: (A AND (NOT B)) OR C
        expected = (Q(search_field__icontains='A') & ~Q(search_field__icontains='B')) | Q(
            search_field__icontains='C'
        )
        assert str(result) == str(expected)

    # Edge cases and special characters
    def test_extra_spaces_between_words(self):
        """Test handling of extra spaces between words."""
        parser = SearchParser('neural    mouse    cortex')
        result = parser.parse()
        expected = (
            Q(search_field__icontains='neural')
            & Q(search_field__icontains='mouse')
            & Q(search_field__icontains='cortex')
        )
        assert str(result) == str(expected)

    def test_leading_and_trailing_spaces(self):
        """Test handling of leading and trailing spaces."""
        parser = SearchParser('   neural mouse   ')
        result = parser.parse()
        expected = Q(search_field__icontains='neural') & Q(search_field__icontains='mouse')
        assert str(result) == str(expected)

    def test_special_characters_in_word(self):
        """Test words with special characters."""
        parser = SearchParser('email@example.com')
        result = parser.parse()
        expected = Q(search_field__icontains='email@example.com')
        assert str(result) == str(expected)

    def test_hyphenated_word(self):
        """Test hyphenated words."""
        parser = SearchParser('two-photon')
        result = parser.parse()
        expected = Q(search_field__icontains='two-photon')
        assert str(result) == str(expected)

    def test_numbers(self):
        """Test parsing numbers."""
        parser = SearchParser('123 456')
        result = parser.parse()
        expected = Q(search_field__icontains='123') & Q(search_field__icontains='456')
        assert str(result) == str(expected)

    def test_only_operators(self):
        """Test string with only operators."""
        parser = SearchParser('AND OR NOT')
        result = parser.parse()
        # These should be consumed as operators, leaving empty Q
        assert str(result) == str(Q())

    def test_consecutive_operators(self):
        """Test consecutive operators."""
        parser = SearchParser('AND AND neural')
        result = parser.parse()
        # First AND is consumed, second AND is consumed, then 'neural'
        # This should parse to just 'neural' since the ANDs have nothing to connect
        expected = Q(search_field__icontains='neural')
        assert str(result) == str(expected)

    def test_operator_at_end(self):
        """Test query ending with an operator."""
        parser = SearchParser('neural AND')
        result = parser.parse()
        # Should parse just 'neural' since AND at end has nothing to connect
        expected = Q(search_field__icontains='neural')
        assert str(result) == str(expected)

    def test_operator_at_beginning(self):
        """Test query starting with an operator (not NOT)."""
        parser = SearchParser('AND neural')
        result = parser.parse()
        # Should parse just 'neural'
        expected = Q(search_field__icontains='neural')
        assert str(result) == str(expected)

    # Real-world scenario tests
    def test_scientific_search_1(self):
        """Test realistic scientific search query."""
        parser = SearchParser('electrophysiology AND (mouse OR rat) NOT behavior')
        result = parser.parse()
        expected = (
            Q(search_field__icontains='electrophysiology')
            & (Q(search_field__icontains='mouse') | Q(search_field__icontains='rat'))
            & ~Q(search_field__icontains='behavior')
        )
        assert str(result) == str(expected)

    def test_scientific_search_2(self):
        """Test search with institution and author."""
        parser = SearchParser('"Allen Institute" OR "MIT"')
        result = parser.parse()
        expected = Q(search_field__icontains='Allen Institute') | Q(search_field__icontains='MIT')
        assert str(result) == str(expected)

    def test_scientific_search_3(self):
        """Test search for specific techniques."""
        parser = SearchParser('"two-photon imaging" AND "calcium imaging" AND mouse')
        result = parser.parse()
        expected = (
            Q(search_field__icontains='two-photon imaging')
            & Q(search_field__icontains='calcium imaging')
            & Q(search_field__icontains='mouse')
        )
        assert str(result) == str(expected)

    def test_date_or_id_search(self):
        """Test search that might include dates or IDs."""
        parser = SearchParser('2023 neural')
        result = parser.parse()
        expected = Q(search_field__icontains='2023') & Q(search_field__icontains='neural')
        assert str(result) == str(expected)

    # Stress tests
    def test_very_long_query(self):
        """Test parsing a very long query."""
        words = ['word' + str(i) for i in range(50)]
        query = ' AND '.join(words)
        parser = SearchParser(query)
        result = parser.parse()
        # Should create a chain of AND operations
        expected = Q(search_field__icontains=words[0])
        for word in words[1:]:
            expected &= Q(search_field__icontains=word)
        assert str(result) == str(expected)

    def test_deeply_nested_parentheses(self):
        """Test deeply nested parentheses."""
        parser = SearchParser('((((neural))))')
        result = parser.parse()
        expected = Q(search_field__icontains='neural')
        assert str(result) == str(expected)

    def test_many_parenthesis_groups(self):
        """Test many separate parenthesis groups."""
        parser = SearchParser('(A) AND (B) AND (C) AND (D)')
        result = parser.parse()
        expected = (
            Q(search_field__icontains='A')
            & Q(search_field__icontains='B')
            & Q(search_field__icontains='C')
            & Q(search_field__icontains='D')
        )
        assert str(result) == str(expected)
