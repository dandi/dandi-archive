"""Gmail-style search query parser for the Dandiset listing endpoint.

Recognizes ``key:value`` operators interleaved with free-text terms.
Quoted phrases (``"like this"``) are kept together — they can be used as
operator values (``technique:"spike sorting"``) or to escape a token
that looks like an operator (``"foo:bar"`` is treated as free text).

Errors are raised explicitly via :class:`SearchSyntaxError`:
- unbalanced quotes
- unknown operator key (with a "did you mean?" suggestion when close)

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
        'file_type',
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
class ParsedSearch:
    free_text: list[str] = field(default_factory=list)
    operators: list[tuple[str, str]] = field(default_factory=list)


def _check_balanced_quotes(query: str) -> None:
    if query.count('"') % 2 != 0:
        raise SearchSyntaxError(
            'Unbalanced quote in search query. Remove the stray quote, or wrap '
            'the intended phrase in matched quotes.'
        )


def _validate_operator_key(key: str) -> None:
    if key in OPERATOR_KEYS:
        return
    suggestions = get_close_matches(key, OPERATOR_KEYS, n=1, cutoff=0.6)
    hint = f' Did you mean "{suggestions[0]}"?' if suggestions else ''
    raise SearchSyntaxError(
        f'Unknown search operator "{key}".{hint} '
        'Wrap the term in double quotes (e.g. "foo:bar") to search for it as text.'
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
            parsed.operators.append((key, match.group('op_qval')))
        elif (free := match.group('free_quoted')) is not None:
            parsed.free_text.append(free)
        else:
            bare = match.group('bare')
            if op_match := _BARE_OP_RE.match(bare):
                key = op_match.group(1)
                _validate_operator_key(key)
                parsed.operators.append((key, op_match.group(2)))
            else:
                parsed.free_text.append(bare)
    return parsed
