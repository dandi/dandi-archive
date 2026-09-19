from __future__ import annotations

from drf_yasg import openapi

from dandiapi.api.models import Asset, Dandiset, Version
from dandiapi.api.views.pagination import DandiPagination

ASSET_ID_PARAM = openapi.Parameter(
    'asset_id',
    openapi.IN_PATH,
    'Asset Identifier',
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_UUID,
    required=True,
    pattern=Asset.UUID_REGEX,
)

DANDISET_PK_PARAM = openapi.Parameter(
    'dandiset__pk',
    openapi.IN_PATH,
    'Dandiset Identifier',
    type=openapi.TYPE_STRING,
    required=True,
    pattern=Dandiset.IDENTIFIER_REGEX,
)

VERSION_PARAM = openapi.Parameter(
    'version',
    openapi.IN_PATH,
    'Dandiset version',
    type=openapi.TYPE_STRING,
    required=True,
    pattern=Version.VERSION_REGEX,
)

VERSIONS_DANDISET_PK_PARAM = openapi.Parameter(
    'versions__dandiset__pk',
    openapi.IN_PATH,
    'Dandiset Identifier of this Version',
    type=openapi.TYPE_STRING,
    required=True,
    pattern=Dandiset.IDENTIFIER_REGEX,
)

VERSIONS_VERSION_PARAM = openapi.Parameter(
    'versions__version',
    openapi.IN_PATH,
    'Dandiset version',
    type=openapi.TYPE_STRING,
    required=True,
    pattern=Version.VERSION_REGEX,
)


# Functional views don't declare a paginator for drf-yasg to inspect, so every paginated
# endpoint documents these by hand.
_pagination = DandiPagination()
PAGINATION_PARAMS = [
    openapi.Parameter(
        DandiPagination.page_query_param,
        openapi.IN_QUERY,
        _pagination.page_query_description,
        type=openapi.TYPE_INTEGER,
        required=False,
        default=1,
    ),
    openapi.Parameter(
        DandiPagination.page_size_query_param,
        openapi.IN_QUERY,
        _pagination.page_size_query_description,
        type=openapi.TYPE_INTEGER,
        required=False,
        default=DandiPagination.page_size,
    ),
]
