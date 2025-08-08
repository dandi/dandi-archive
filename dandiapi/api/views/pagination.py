from __future__ import annotations

from collections import OrderedDict

from django.core.paginator import Page, Paginator
from django.utils.functional import cached_property
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DandiPagination(PageNumberPagination):
    page_size = 100
    max_page_size = 1000
    page_size_query_param = 'page_size'

    @cached_property
    def page_size_query_description(self):
        return f'{super().page_size_query_description[:-1]} (maximum {self.max_page_size}).'


"""
The below code provides a custom pagination implementation, as the existing `PageNumberPagination`
class returns a `count` field for every page returned. This can be very inefficient on large tables,
and in reality, the count is only necessary on the first page of results. This module implements
such a pagination scheme, only returning 'count' on the first page of results.
"""


class LazyPage(Page):
    """
    A page class that doesn't call .count() on the queryset it's paging from.

    This class should be used with `LazyPaginator` unless you know what you're doing.
    """

    # Override to store the real object list under self._object_last
    def __init__(self, object_list, number, paginator):
        self._object_list = list(object_list)
        self.number = number
        self.paginator = paginator

    # Override to prevent returning the extra record
    @cached_property
    def object_list(self):
        return self._object_list[: self.paginator.per_page]

    # Because we fetch one extra object to check for more rows, we know that if the number of
    # objects returned is the page size or less, we have no more pages.
    def has_next(self) -> bool:
        return len(self._object_list) > self.paginator.per_page

    # Override to prevent calling `.count` on the queryset. To my knowledge we don't use this.
    def end_index(self) -> int:
        raise NotImplementedError


class LazyPaginator(Paginator):
    """A Paginator that doesn't call .count() on the queryset."""

    # Set this to infinity so that inherited code doesn't assume we're done paginating
    num_pages = float('inf')

    def page(self, number):
        """Return a page with one extra row, used to determine if there are more pages."""
        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page

        # Intentionally fetch one extra to see if there are any more pages left
        top = bottom + self.per_page + 1

        return self._get_page(self.object_list[bottom:top], number, self)

    def _get_page(self, *args, **kwargs):
        return LazyPage(*args, **kwargs)


class LazyPagination(PageNumberPagination):
    page_size = 100
    max_page_size = 1000
    page_size_query_param = 'page_size'
    django_paginator_class = LazyPaginator

    # Set to always false since we only know the full number of pages on page 1
    display_page_controls = False

    # Define as empty to prevent `get_page_number` from calling `count`
    last_page_strings = ()

    # Set to None to prevent `paginate_queryset` from setting `display_page_controls` to True
    template = None

    @cached_property
    def page_size_query_description(self):
        return f'{super().page_size_query_description[:-1]} (maximum {self.max_page_size}).'

    def get_paginated_response(self, data) -> Response:
        """Overridden to only include the count of the queryset on the first page."""
        if self.page is None:
            raise RuntimeError('Paginator is uninitialized.')
        page_dict = OrderedDict(
            [
                ('count', self.page.paginator.count if self.page.number == 1 else None),
                ('next', self.get_next_link()),
                ('previous', self.get_previous_link()),
                ('results', data),
            ]
        )

        return Response(page_dict)
