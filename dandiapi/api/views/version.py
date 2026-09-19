from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from dandiapi.api.models import Dandiset, Version
from dandiapi.api.services import audit
from dandiapi.api.services.embargo.exceptions import DandisetUnembargoInProgressError
from dandiapi.api.services.permissions.dandiset import (
    require_dandiset_owner_or_403,
    require_dandiset_read_access,
)
from dandiapi.api.services.publish import publish_dandiset
from dandiapi.api.tasks import delete_doi_task
from dandiapi.api.views.common import DANDISET_PK_PARAM, PAGINATION_PARAMS, VERSION_PARAM
from dandiapi.api.views.pagination import DandiPagination
from dandiapi.api.views.serializers import (
    PublishVersionSerializer,
    VersionDetailSerializer,
    VersionListQuerySerializer,
    VersionMetadataSerializer,
    VersionSerializer,
)

if TYPE_CHECKING:
    from rest_framework.request import Request


def get_readable_version_or_404(request: Request, *, dandiset_pk: str, version: str) -> Version:
    """
    Fetch a version by dandiset ID and version, ensuring the user may read its dandiset.

    The version and its dandiset are fetched together, so that the common case costs a
    single query. When the version doesn't exist, its dandiset is checked on its own, so
    that embargoed dandisets don't disclose which of their versions exist.
    """
    version_object = (
        Version.objects.select_related('dandiset')
        .filter(dandiset__pk=dandiset_pk, version=version)
        .first()
    )
    if version_object is None:
        require_dandiset_read_access(get_object_or_404(Dandiset, pk=dandiset_pk), request.user)
        raise NotFound

    require_dandiset_read_access(version_object.dandiset, request.user)
    return version_object


@swagger_auto_schema(
    method='GET',
    query_serializer=VersionListQuerySerializer,
    manual_parameters=[DANDISET_PK_PARAM, *PAGINATION_PARAMS],
    responses={200: VersionSerializer(many=True)},
    operation_summary='List the versions of a dandiset.',
)
@api_view(['GET', 'HEAD'])
def version_list_view(request: Request, dandiset__pk: str) -> Response:
    dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
    require_dandiset_read_access(dandiset, request.user)

    query_serializer = VersionListQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)

    versions = Version.objects.select_related('dandiset').filter(dandiset=dandiset)
    if 'created' in query_serializer.validated_data:
        versions = versions.filter(created=query_serializer.validated_data['created'])
    versions = versions.order_by(*(query_serializer.validated_data['order'] or ['created']))

    paginator = DandiPagination()
    page = paginator.paginate_queryset(versions, request=request)
    serializer = VersionSerializer(page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)


def _retrieve_version(request: Request, dandiset__pk: str, version: str) -> Response:
    version_object = get_readable_version_or_404(request, dandiset_pk=dandiset__pk, version=version)
    return Response(version_object.metadata, status=status.HTTP_200_OK)


@require_dandiset_owner_or_403('dandiset__pk')
def _update_version(request: Request, dandiset__pk: str, version: str) -> Response:
    """Update the metadata of a version."""
    version_object = get_readable_version_or_404(request, dandiset_pk=dandiset__pk, version=version)
    if version_object.version != 'draft':
        return Response(
            'Only draft versions can be modified.',
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
    if version_object.dandiset.unembargo_in_progress:
        raise DandisetUnembargoInProgressError

    serializer = VersionMetadataSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    name = serializer.validated_data['name']

    # Strip away any computed fields from the new metadata
    new_metadata = Version.strip_metadata(serializer.validated_data['metadata'])

    with transaction.atomic():
        # Re-query for the version, this time using a SELECT FOR UPDATE to
        # ensure the object doesn't change out from under us.
        locked_version = Version.objects.select_for_update().get(id=version_object.id)
        old_metadata = Version.strip_metadata(locked_version.metadata)

        # Only save version if metadata has actually changed
        if (name, new_metadata) != (locked_version.name, old_metadata):
            locked_version.name = name
            locked_version.metadata = new_metadata
            locked_version.status = Version.Status.PENDING
            locked_version.save()

            audit.update_metadata(
                dandiset=locked_version.dandiset,
                user=request.user,
                metadata=locked_version.metadata,
            )

    serializer = VersionDetailSerializer(instance=locked_version)
    return Response(serializer.data, status=status.HTTP_200_OK)


def _destroy_version(request: Request, dandiset__pk: str, version: str) -> Response:
    """
    Delete a version.

    Deletes a version. Only published versions can be deleted, and only by
    admin users.
    """
    version_object = get_readable_version_or_404(request, dandiset_pk=dandiset__pk, version=version)
    if version_object.version == 'draft':
        return Response(
            'Cannot delete draft versions',
            status=status.HTTP_403_FORBIDDEN,
        )
    if not request.user.is_superuser:
        return Response(
            'Cannot delete published versions',
            status=status.HTTP_403_FORBIDDEN,
        )
    doi = version_object.doi
    version_object.delete()
    if doi is not None:
        delete_doi_task.delay(doi)
    return Response(None, status=status.HTTP_204_NO_CONTENT)


@swagger_auto_schema(
    method='GET',
    responses={
        200: 'The version metadata.',
    },
    manual_parameters=[DANDISET_PK_PARAM, VERSION_PARAM],
)
@swagger_auto_schema(
    method='PUT',
    request_body=VersionMetadataSerializer,
    responses={200: VersionDetailSerializer},
    manual_parameters=[DANDISET_PK_PARAM, VERSION_PARAM],
    operation_summary='Update the metadata of a version.',
)
@swagger_auto_schema(
    method='DELETE',
    manual_parameters=[DANDISET_PK_PARAM, VERSION_PARAM],
    operation_summary='Delete a version.',
    operation_description=(
        'Deletes a version. Only published versions can be deleted, and only by admin users.'
    ),
)
@api_view(['GET', 'HEAD', 'PUT', 'DELETE'])
def version_detail_view(request: Request, **kwargs) -> Response:
    if request.method == 'PUT':
        return _update_version(request, **kwargs)
    if request.method == 'DELETE':
        return _destroy_version(request, **kwargs)
    return _retrieve_version(request, **kwargs)


@swagger_auto_schema(
    method='GET',
    operation_id='dandisets_versions_info',
    manual_parameters=[DANDISET_PK_PARAM, VERSION_PARAM],
    responses={200: VersionDetailSerializer},
    operation_summary='Django serialization of a version.',
)
@api_view(['GET', 'HEAD'])
def version_info_view(request: Request, dandiset__pk: str, version: str) -> Response:
    """Django serialization of a version."""
    version_object = get_readable_version_or_404(request, dandiset_pk=dandiset__pk, version=version)
    serializer = VersionDetailSerializer(instance=version_object, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='POST',
    operation_id='dandisets_versions_publish',
    request_body=PublishVersionSerializer,
    manual_parameters=[DANDISET_PK_PARAM, VERSION_PARAM],
    responses={200: VersionSerializer},
    operation_summary='Publish a version.',
)
@api_view(['POST'])
@require_dandiset_owner_or_403('dandiset__pk')
def version_publish_view(request: Request, dandiset__pk: str, version: str) -> Response:
    """Publish a version."""
    if version != 'draft':
        return Response(
            'Only draft versions can be published',
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
    serializer = PublishVersionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    release_notes: str | None = serializer.validated_data.get('release_notes')

    version_object = get_readable_version_or_404(request, dandiset_pk=dandiset__pk, version=version)
    publish_dandiset(
        user=request.user, dandiset=version_object.dandiset, release_notes=release_notes
    )
    return Response(None, status=status.HTTP_202_ACCEPTED)
