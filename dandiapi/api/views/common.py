from __future__ import annotations

from drf_yasg import openapi

from dandiapi.api.views.pagination import DandiPagination

ASSET_ID_PARAM = openapi.Parameter(
    'asset_id',
    openapi.IN_PATH,
    'Asset Identifier',
    type=openapi.TYPE_STRING,
    required=True,
    pattern=r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',
)

DANDISET_PK_PARAM = openapi.Parameter(
    'dandiset__pk',
    openapi.IN_PATH,
    'Dandiset Identifier',
    type=openapi.TYPE_STRING,
    required=True,
)

VERSION_PARAM = openapi.Parameter(
    'version',
    openapi.IN_PATH,
    'Dandiset version',
    type=openapi.TYPE_STRING,
    required=True,
    pattern=r'(0\.\d{6}\.\d{4})|draft',
)

VERSIONS_DANDISET_PK_PARAM = openapi.Parameter(
    'versions__dandiset__pk',
    openapi.IN_PATH,
    'Dandiset Identifier of this Version',
    type=openapi.TYPE_STRING,
    required=True,
)

VERSIONS_VERSION_PARAM = openapi.Parameter(
    'versions__version',
    openapi.IN_PATH,
    'Dandiset version',
    type=openapi.TYPE_STRING,
    required=True,
    pattern=r'(0\.\d{6}\.\d{4})|draft',
)


PAGINATION_PARAMS = [
    openapi.Parameter(
        DandiPagination.page_query_param,
        openapi.IN_QUERY,
        'The page number',
        type=openapi.TYPE_INTEGER,
        required=False,
        default=1,
    ),
    openapi.Parameter(
        DandiPagination.page_size_query_param,
        openapi.IN_QUERY,
        'The page size',
        type=openapi.TYPE_INTEGER,
        required=False,
        default=DandiPagination.page_size,
    ),
]
