from __future__ import annotations

from dandiapi.api.services.search.parser import SearchSyntaxError, parse_search

# `parse_search` is the only entry point used outside this package; the view
# layer catches `SearchSyntaxError` and surfaces it as a 400. ParsedSearch /
# OPERATOR_KEYS are internal — import from .parser directly if you need them.
__all__ = ['SearchSyntaxError', 'parse_search']
