"""Custom template filters for DANDI Archive."""

from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def filesizeformat_tib(bytes_value):
    """Convert bytes to TiB format."""
    if not bytes_value:
        return '0 TiB'

    tib_value = bytes_value / (1024**4)
    return f'{tib_value:.0f} TiB'
