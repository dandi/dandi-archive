from rest_framework.pagination import PageNumberPagination

max_page_size = 1000


class DandiPagination(PageNumberPagination):
    page_size = 25
    max_page_size = max_page_size
    page_size_query_param = 'page_size'

    page_size_query_description = (
        f'{PageNumberPagination.page_size_query_description[:-1]} (maximum {max_page_size}).'
    )
