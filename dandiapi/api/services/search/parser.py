"""Gmail-style search query parser for the Dandiset listing endpoint.

Recognizes ``key:value`` operators interleaved with free-text terms. The
query syntax is defined by a Lark grammar (``_GRAMMAR``), and the parse tree
is turned into a :class:`ParsedSearch` by ``_SearchTransformer``, or compiled
straight into a Postgres query by ``filters.build_search_filter``.
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

from lark import Lark, Token, Transformer, Tree, v_args
from lark.exceptions import UnexpectedInput, VisitError

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


def operator_from_token(token: Token) -> Operator:
    """Build a validated :class:`Operator` from a ``*_OPERATOR`` token."""
    key, _, value = str(token).partition(':')
    _validate_operator_key(key)
    if token.type == 'QUOTED_OPERATOR':
        value = value[1:-1]
    return Operator(key, value)


def text_from_token(token: Token) -> str:
    """Return the free text carried by a ``PHRASE`` or ``WORD`` token."""
    text = str(token)
    return text[1:-1] if token.type == 'PHRASE' else text


@v_args(inline=True)
class _SearchTransformer(Transformer):
    """Turn the parse tree into a :class:`ParsedSearch`."""

    def quoted_operator(self, token):
        return operator_from_token(token)

    bare_operator = quoted_operator

    def phrase(self, token):
        return text_from_token(token)

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


def parse_tree(query: str) -> Tree:
    """Parse ``query`` into a Lark tree, after the length and quote checks.

    Each child of the returned ``start`` tree is one term, labelled
    ``quoted_operator``, ``bare_operator``, ``phrase`` or ``word``. Operator
    keys are not validated here; that happens when the tree is transformed.
    """
    if len(query) > _MAX_SEARCH_LENGTH:
        raise SearchSyntaxError(
            f'Search query is too long ({len(query)} characters; max {_MAX_SEARCH_LENGTH}).'
        )

    _check_balanced_quotes(query)

    try:
        return _parser.parse(query)
    except UnexpectedInput as exc:
        raise SearchSyntaxError(f'Could not parse search query: {exc}') from exc


def transform_tree(transformer: Transformer, tree: Tree):
    """Run ``transformer`` over ``tree``, surfacing SearchSyntaxError unwrapped.

    Lark wraps exceptions raised inside transformer callbacks in a VisitError;
    callers expect the original :class:`SearchSyntaxError`.
    """
    try:
        return transformer.transform(tree)
    except VisitError as exc:
        if isinstance(exc.orig_exc, SearchSyntaxError):
            raise exc.orig_exc from None
        raise


def parse_search(query: str) -> ParsedSearch:
    if not query:
        return ParsedSearch()
    return transform_tree(_SearchTransformer(), parse_tree(query))
