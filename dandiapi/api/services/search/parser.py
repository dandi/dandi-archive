"""Gmail-style search query parser for the Dandiset listing endpoint.

Recognizes ``key:value`` operators interleaved with free-text terms.
Quoted phrases (``"like this"``) are kept together — they can be used as
operator values (``technique:"spike sorting"``) or to escape a token
that looks like an operator (``"foo:bar"`` is treated as free text).

Errors are raised explicitly via :class:`SearchSyntaxError`:
- unbalanced quotes
- unknown operator key (with a "did you mean?" suggestion when close)
- reserved syntax (see below)

Grammar, in EBNF. ``key`` must be one of :data:`OPERATOR_KEYS`, and the
first matching alternative of ``term`` wins::

    query    = [ ws ] , [ term , { ws , term } ] , [ ws ] ;
    term     = operator | phrase | word ;
    operator = key , ":" , ( phrase | token ) ;
    phrase   = '"' , { any character except '"' } , '"' ;
    word     = token - reserved ;
    token    = non-space , { non-space } ;
    key      = ( "a" .. "z" | "_" ) , { "a" .. "z" | "_" } ;
    reserved = "AND" | "OR" | "NOT"
             | "-" , key , ":" , { non-space }
             | { non-space } , ( "(" | ")" ) , { non-space } ;
    ws       = " " , { " " } ;

Terms combine with AND. The ``reserved`` forms are rejected with a 400 so
that boolean operators, negation, and grouping can be added later without
changing the meaning of queries people already use. Quoting a reserved form
searches for it as text.

The view layer translates :class:`SearchSyntaxError` into a 400 response.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import get_close_matches
import re

OPERATOR_KEYS: frozenset[str] = frozenset(
    {
        'created_before',
        'created_after',
        'modified_before',
        'modified_after',
        'published_before',
        'published_after',
        'species',
        'approach',
        'technique',
        'standard',
        'variable',
        'owner',
    }
)

# A token in the input is one of:
#   key:"quoted value"       — operator with quoted value
#   "quoted text"            — quoted free text (escapes operator-like content)
#   key:value                — operator (key validated against OPERATOR_KEYS)
#   bare_token               — free text
#
# We deliberately match `key:"value"` and `"value"` *before* the bare-token
# alternative so quoted segments stay together.
_TOKEN_RE = re.compile(
    r'(?P<op_key>[a-z_]+):"(?P<op_qval>[^"]*)"'
    r'|"(?P<free_quoted>[^"]*)"'
    r'|(?P<bare>\S+)'
)
_BARE_OP_RE = re.compile(r'^([a-z_]+):(.+)$')


# Defense-in-depth: cap search-term length so an unauthenticated caller can't
# force the parser/Postgres to materialize a multi-MB query string. Generous
# enough that any reasonable interactive query fits.
_MAX_SEARCH_LENGTH = 1024


class SearchSyntaxError(ValueError):
    """Raised when a search query can't be parsed."""


@dataclass
class Operator:
    """One parsed `key:value` operator."""

    key: str
    value: str


@dataclass
class ParsedSearch:
    free_text: list[str] = field(default_factory=list)
    operators: list[Operator] = field(default_factory=list)


def _check_balanced_quotes(query: str) -> None:
    if query.count('"') % 2 != 0:
        raise SearchSyntaxError(
            'Unbalanced quote in search query. Remove the stray quote, or wrap '
            'the intended phrase in matched quotes.'
        )


def _validate_operator_key(key: str) -> None:
    if key in OPERATOR_KEYS:
        return
    if key == 'file_type':
        # Removed operator; there is no close-enough key for the generic
        # suggestion below to fire, so point at the replacements explicitly.
        raise SearchSyntaxError(
            'The "file_type" operator has been removed. Use standard: to match '
            'a data standard (e.g. standard:nwb), or the file type filter in '
            'the search sidebar.'
        )
    suggestions = get_close_matches(key, OPERATOR_KEYS, n=1, cutoff=0.6)
    hint = f' Did you mean "{suggestions[0]}"?' if suggestions else ''
    raise SearchSyntaxError(
        f'Unknown search operator "{key}".{hint} '
        'Wrap the term in double quotes (e.g. "foo:bar") to search for it as text.'
    )


# Uppercase boolean words are reserved; lowercase "and"/"or"/"not" are
# ordinary free text.
_RESERVED_WORDS = frozenset({'AND', 'OR', 'NOT'})
_NEGATED_OP_RE = re.compile(r'^-[a-z_]+:')


def _check_reserved(token: str) -> None:
    """Reject unquoted syntax reserved for boolean operators, negation, and grouping."""
    if token in _RESERVED_WORDS:
        raise SearchSyntaxError(
            f'"{token}" is reserved for boolean search, which is not supported yet. '
            'Terms are always combined with AND. Wrap it in double quotes '
            f'("{token}") to search for the word.'
        )
    if _NEGATED_OP_RE.match(token):
        raise SearchSyntaxError(
            f'"{token}": excluding results with a leading "-" is not supported yet. '
            f'Wrap the term in double quotes ("{token}") to search for it as text.'
        )
    if '(' in token or ')' in token:
        raise SearchSyntaxError(
            f'"{token}": parentheses are reserved for grouping, which is not supported '
            'yet. Wrap the text in double quotes to search for it, e.g. "(CA1)".'
        )


def parse_search(query: str) -> ParsedSearch:
    parsed = ParsedSearch()
    if not query:
        return parsed
    if len(query) > _MAX_SEARCH_LENGTH:
        raise SearchSyntaxError(
            f'Search query is too long ({len(query)} characters; max {_MAX_SEARCH_LENGTH}).'
        )

    _check_balanced_quotes(query)

    for match in _TOKEN_RE.finditer(query):
        if (key := match.group('op_key')) is not None:
            _validate_operator_key(key)
            parsed.operators.append(Operator(key, match.group('op_qval')))
        elif (free := match.group('free_quoted')) is not None:
            parsed.free_text.append(free)
        else:
            bare = match.group('bare')
            _check_reserved(bare)
            if op_match := _BARE_OP_RE.match(bare):
                key = op_match.group(1)
                _validate_operator_key(key)
                parsed.operators.append(Operator(key, op_match.group(2)))
            else:
                parsed.free_text.append(bare)
    return parsed
