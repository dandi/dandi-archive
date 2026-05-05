"""Gmail-style search query parser for the Dandiset listing endpoint.

Recognizes ``key:value`` operators interleaved with free-text terms. Quoted
phrases (``"like this"``) are treated as a single token. Tokens whose key is
not in ``OPERATOR_KEYS`` are demoted to free text — Gmail behavior, easier on
the user than a hard parse error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import shlex

OPERATOR_KEYS: frozenset[str] = frozenset(
    {
        'created_before',
        'created_after',
        'modified_before',
        'modified_after',
        'published_before',
        'published_after',
        'has_species',
        'has_approach',
        'has_technique',
        'has_standard',
        'has_file_type',
    }
)

_OPERATOR_RE = re.compile(r'^([a-z_]+):(.+)$', re.DOTALL)


@dataclass
class ParsedSearch:
    free_text: list[str] = field(default_factory=list)
    operators: list[tuple[str, str]] = field(default_factory=list)


def _tokenize(query: str) -> list[str]:
    # shlex handles quoted phrases; posix=True strips the quotes and preserves
    # internal whitespace. Fall back to a plain split if shlex chokes on an
    # unbalanced quote — we never want a 500 from a weird query string.
    try:
        return shlex.split(query, posix=True)
    except ValueError:
        return query.split()


def parse_search(query: str) -> ParsedSearch:
    parsed = ParsedSearch()
    if not query:
        return parsed

    for token in _tokenize(query):
        if (match := _OPERATOR_RE.match(token)) and match.group(1) in OPERATOR_KEYS:
            parsed.operators.append((match.group(1), match.group(2)))
        else:
            parsed.free_text.append(token)
    return parsed
