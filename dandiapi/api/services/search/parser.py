"""GitHub-style search query parser for the Dandiset listing endpoint.

Recognizes ``key:value`` operators interleaved with free-text terms. The
query syntax is defined by a Lark grammar (``_GRAMMAR``), and
``_SearchTransformer`` turns the parse tree into a :class:`ParsedSearch`,
which ``filters.build_search_filter`` compiles into a Postgres query.
Quoted phrases (``"like this"``) are kept together — they can be used as
operator values (``technique:"spike sorting"``) or to escape a token
that looks like an operator (``"foo:bar"`` is treated as free text).

Errors are raised explicitly via :class:`SearchSyntaxError`:
- unbalanced quotes
- unknown operator key (with a "did you mean?" suggestion when close)
- operator with an empty value, or a date operator with a malformed date

Terms are validated in order, so the error reported is the first bad term's.

The view layer translates :class:`SearchSyntaxError` into a 400 response.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from difflib import get_close_matches

from lark import Lark, Token, Transformer, v_args
from lark.exceptions import UnexpectedInput, VisitError

from dandiapi.api.services.search.anatomy import ANATOMY_ONTOLOGIES

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
        'anatomy_exact',
    }
)

# URL schemes look like operator keys to the lexer. A pasted URL is far more
# likely to be something to search for than a mistyped operator.
_URL_SCHEMES: frozenset[str] = frozenset({'http', 'https'})

# The query grammar. A query is a whitespace-separated sequence of terms, and
# each term is one of:
#
#   key:"quoted value"   operator with a quoted value
#   key:value            operator with a bare value
#   "quoted text"        quoted free text (escapes operator-like content)
#   word                 free text
#
# The lexer tries terminals in priority order (higher first), so a quoted
# operator wins over a bare operator, and an operator wins over a plain word.
# Operator keys are not enumerated here: any lowercase key is accepted by the
# grammar, and `_SearchTransformer` validates it against OPERATOR_KEYS so that
# unknown keys get a "did you mean?" message instead of a generic parse error.
_GRAMMAR = r"""
    start: term*

    ?term: QUOTED_OPERATOR -> quoted_operator
         | BARE_OPERATOR   -> bare_operator
         | PHRASE          -> phrase
         | WORD            -> word

    _KEY: /[a-z_]+/
    _QUOTED: /"[^"]*"/

    QUOTED_OPERATOR.4: _KEY ":" _QUOTED
    PHRASE.3: _QUOTED
    BARE_OPERATOR.2: _KEY ":" /\S+/
    WORD.1: /\S+/

    %ignore /\s+/
"""


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


def _validate_operator_key(key: str, value: str) -> None:
    if key in OPERATOR_KEYS:
        return
    if key.upper() in ANATOMY_ONTOLOGIES:
        # A bare lowercase CURIE such as `uberon:0002421`.
        raise SearchSyntaxError(
            f'Unknown search operator "{key}". Did you mean "anatomy_exact:{key.upper()}:{value}"?'
        )
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


def parse_date(operator: str, value: str) -> datetime:
    """Parse a date operator's ``YYYY-MM-DD`` value as midnight UTC."""
    try:
        return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=UTC)
    except ValueError as exc:
        raise SearchSyntaxError(
            f'Invalid date for "{operator}": {value!r}. Use YYYY-MM-DD.'
        ) from exc


@v_args(inline=True)
class _SearchTransformer(Transformer):
    """Turn the parse tree into a :class:`ParsedSearch`, validating each term."""

    def quoted_operator(self, token: Token) -> Operator | str:
        key, _, value = str(token).partition(':')
        if token.type == 'BARE_OPERATOR' and key in _URL_SCHEMES:
            return str(token)  # a pasted URL is free text
        if token.type == 'QUOTED_OPERATOR':
            value = value[1:-1]
        _validate_operator_key(key, value)
        value = value.strip()
        if not value:
            raise SearchSyntaxError(f'Operator "{key}" requires a value (e.g. {key}:something).')
        if key.endswith(('_before', '_after')):
            parse_date(key, value)
        return Operator(key, value)

    bare_operator = quoted_operator

    def phrase(self, token: Token) -> str:
        text = str(token)
        return text[1:-1] if token.type == 'PHRASE' else text

    word = phrase

    @v_args(inline=False)
    def start(self, terms):
        parsed = ParsedSearch()
        for term in terms:
            if isinstance(term, Operator):
                parsed.operators.append(term)
            else:
                parsed.free_text.append(term)
        return parsed


_parser = Lark(_GRAMMAR, parser='lalr', lexer='basic')


def parse_search(query: str) -> ParsedSearch:
    """Parse and validate ``query``, raising :class:`SearchSyntaxError` if it's bad."""
    if not query:
        return ParsedSearch()
    if len(query) > _MAX_SEARCH_LENGTH:
        raise SearchSyntaxError(
            f'Search query is too long ({len(query)} characters; max {_MAX_SEARCH_LENGTH}).'
        )

    _check_balanced_quotes(query)

    try:
        tree = _parser.parse(query)
    except UnexpectedInput as exc:
        raise SearchSyntaxError(f'Could not parse search query: {exc}') from exc

    try:
        return _SearchTransformer().transform(tree)
    except VisitError as exc:
        # Lark wraps errors raised inside transformer callbacks; surface ours as-is.
        if isinstance(exc.orig_exc, SearchSyntaxError):
            raise exc.orig_exc from None
        raise
