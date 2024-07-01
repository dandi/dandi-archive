from __future__ import annotations

from django.db import transaction
from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg.utils import no_body, swagger_auto_schema
from guardian.decorators import permission_required_or_403
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandiapi.api.models import Dandiset, Version
from dandiapi.api.services.embargo.exceptions import DandisetUnembargoInProgressError
from dandiapi.api.services.publish import publish_dandiset
from dandiapi.api.tasks import delete_doi_task
from dandiapi.api.views.common import DANDISET_PK_PARAM, VERSION_PARAM
from dandiapi.api.views.pagination import DandiPagination
from dandiapi.api.views.serializers import (
    VersionDetailSerializer,
    VersionMetadataSerializer,
    VersionSerializer,
)


class VersionFilter(filters.FilterSet):
    order = filters.OrderingFilter(fields=['created'])

    class Meta:
        model = Version
        fields = ['created']


class VersionViewSet(NestedViewSetMixin, DetailSerializerMixin, ReadOnlyModelViewSet):
    queryset = Version.objects.all().select_related('dandiset').order_by('created')

    serializer_class = VersionSerializer
    serializer_detail_class = VersionDetailSerializer
    pagination_class = DandiPagination

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = VersionFilter

    lookup_field = 'version'
    lookup_value_regex = Version.VERSION_REGEX

    def get_queryset(self):
        # We need to check the dandiset to see if it's embargoed, and if so whether or not the
        # user has ownership
        dandiset = get_object_or_404(Dandiset, pk=self.kwargs['dandiset__pk'])
        if dandiset.embargo_status != Dandiset.EmbargoStatus.OPEN:
            if not self.request.user.is_authenticated:
                # Clients must be authenticated to access it
                raise NotAuthenticated
            if not self.request.user.has_perm('owner', dandiset):
                # The user does not have ownership permission
                raise PermissionDenied
        return super().get_queryset()

    @swagger_auto_schema(
        responses={
            200: 'The version metadata.',
        },
        manual_parameters=[DANDISET_PK_PARAM, VERSION_PARAM],
    )
    def retrieve(self, request, **kwargs):
        version = self.get_object()
        return Response(version.metadata, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[DANDISET_PK_PARAM, VERSION_PARAM],
        responses={200: VersionDetailSerializer},
    )
    @action(detail=True, methods=['GET'])
    def info(self, request, **kwargs):
        """Django serialization of a version."""
        version = self.get_object()
        serializer = VersionDetailSerializer(instance=version)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=VersionMetadataSerializer,
        responses={200: VersionDetailSerializer},
        manual_parameters=[DANDISET_PK_PARAM, VERSION_PARAM],
    )
    @method_decorator(permission_required_or_403('owner', (Dandiset, 'pk', 'dandiset__pk')))
    def update(self, request, **kwargs):
        """Update the metadata of a version."""
        version: Version = self.get_object()
        if version.version != 'draft':
            return Response(
                'Only draft versions can be modified.',
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        if version.dandiset.unembargo_in_progress:
            raise DandisetUnembargoInProgressError

        serializer = VersionMetadataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data['name']
        new_metadata = serializer.validated_data['metadata']

        # Strip away any computed fields from current and new metadata
        new_metadata = Version.strip_metadata(new_metadata)

        with transaction.atomic():
            # Re-query for the version, this time using a SELECT FOR UPDATE to
            # ensure the object doesn't change out from under us.
            locked_version = Version.objects.select_for_update().get(id=version.id)
            old_metadata = Version.strip_metadata(locked_version.metadata)

            # Only save version if metadata has actually changed
            if (name, new_metadata) != (locked_version.name, old_metadata):
                locked_version.name = name
                locked_version.metadata = new_metadata
                locked_version.status = Version.Status.PENDING
                locked_version.save()

        serializer = VersionDetailSerializer(instance=locked_version)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=no_body,
        manual_parameters=[DANDISET_PK_PARAM, VERSION_PARAM],
        responses={200: VersionSerializer},
    )
    @action(detail=True, methods=['POST'])
    @method_decorator(permission_required_or_403('owner', (Dandiset, 'pk', 'dandiset__pk')))
    def publish(self, request, **kwargs):
        """Publish a version."""
        if kwargs['version'] != 'draft':
            return Response(
                'Only draft versions can be published',
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        publish_dandiset(user=request.user, dandiset=self.get_object().dandiset)
        return Response(None, status=status.HTTP_202_ACCEPTED)

    @swagger_auto_schema(
        manual_parameters=[DANDISET_PK_PARAM, VERSION_PARAM],
    )
    def destroy(self, request, **kwargs):
        """
        Delete a version.

        Deletes a version. Only published versions can be deleted, and only by
        admin users.
        """
        version: Version = self.get_object()
        if version.version == 'draft':
            return Response(
                'Cannot delete draft versions',
                status=status.HTTP_403_FORBIDDEN,
            )
        if not request.user.is_superuser:
            return Response(
                'Cannot delete published versions',
                status=status.HTTP_403_FORBIDDEN,
            )
        doi = version.doi
        version.delete()
        if doi is not None:
            delete_doi_task.delay(doi)
        return Response(None, status=status.HTTP_204_NO_CONTENT)
