from __future__ import annotations

from typing import TYPE_CHECKING

from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, PermissionDenied

from dandiapi.api.asset_paths import PathEntry, get_child_paths, get_path_entries, get_path_entry
from dandiapi.api.models.version import Version
from dandiapi.api.services.permissions.dandiset import is_dandiset_owner
from dandiapi.api.views.common import PAGINATION_PARAMS
from dandiapi.api.views.pagination import DandiPagination

from .serializers import AtPathQuerySerializer, PathResultSerializer

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from rest_framework.request import Request

    from dandiapi.api.models.dandiset import Dandiset


class AtPathResults:
    """
    The file or folder at a path, followed by the children of that path, ordered by path.

    Either of these may be omitted. This implements just enough to be paginated, so that the
    children of a path are only ever fetched one page at a time.
    """

    def __init__(
        self, *, version: Version, entry: PathEntry | None, children: QuerySet | None
    ) -> None:
        self._version = version
        self._entries = [entry] if entry is not None else []
        self._children = children

    def count(self) -> int:
        return len(self._entries) + (self._children.count() if self._children is not None else 0)

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, key: slice) -> list[PathEntry]:
        start = key.start or 0
        entries = self._entries[start : key.stop]
        if self._children is None:
            return entries

        # The children follow the entry of the path itself, so their indexes are offset by it
        offset = len(self._entries)
        stop = None if key.stop is None else max(key.stop - offset, 0)
        children = self._children[max(start - offset, 0) : stop]

        return [*entries, *get_path_entries(children, self._version)]


def get_atpath_results(*, version: Version, path: str, children: bool) -> AtPathResults:
    # Handle root path case explicitly, as there's no entry for the root path itself
    if path == '':
        return AtPathResults(
            version=version, entry=None, children=get_child_paths(version) if children else None
        )

    entry = get_path_entry(version, path)

    # Only a folder has children to show
    show_children = children and entry is not None and entry.asset is None
    return AtPathResults(
        version=version,
        entry=entry,
        children=get_child_paths(version, path) if show_children else None,
    )


@swagger_auto_schema(
    query_serializer=AtPathQuerySerializer,
    manual_parameters=PAGINATION_PARAMS,
    responses={200: PathResultSerializer(many=True)},
    method='GET',
)
@api_view(['GET'])
def atpath(request: Request):
    query_serializer = AtPathQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)

    params = query_serializer.validated_data
    version = get_object_or_404(
        Version.objects.select_related('dandiset'),
        dandiset_id=int(params['dandiset_id']),
        version=params['version_id'],
    )
    dandiset: Dandiset = version.dandiset

    # Ensure embargoed dandisets are only accessed by owners
    if dandiset.embargoed and not is_dandiset_owner(dandiset, request.user):
        raise PermissionDenied

    # This endpoint allows an ending slash for folders,
    # but the AssetPath implementation prohibits it
    path: str = params['path']
    endslash = path.endswith('/')
    path = path.rstrip('/')

    results = get_atpath_results(version=version, path=path, children=params['children'])

    # Handle special behavior if results not found
    if path != '':
        first = next(iter(results[:1]), None)
        if first is None:
            raise NotFound(detail=f'Folder or asset not found at {path}')
        if endslash and first.asset is not None:
            raise NotFound(detail=f'Folder not found at {path}')

    # Paginate
    paginator = DandiPagination()
    result_page = paginator.paginate_queryset(results, request=request)
    serializer = PathResultSerializer(
        instance=result_page, many=True, context={'metadata': params['metadata']}
    )

    return paginator.get_paginated_response(serializer.data)
