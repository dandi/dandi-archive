from django.db import transaction
from django.utils.decorators import method_decorator
from drf_yasg.utils import no_body, swagger_auto_schema
from guardian.decorators import permission_required_or_403
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandiapi.api import doi
from dandiapi.api.models import Dandiset, Version
from dandiapi.api.tasks import delete_doi_task, write_manifest_files
from dandiapi.api.views.common import DANDISET_PK_PARAM, VERSION_PARAM, DandiPagination
from dandiapi.api.views.serializers import (
    VersionDetailSerializer,
    VersionMetadataSerializer,
    VersionSerializer,
)


class VersionViewSet(NestedViewSetMixin, DetailSerializerMixin, ReadOnlyModelViewSet):
    queryset = Version.objects.all().select_related('dandiset').order_by('created')

    serializer_class = VersionSerializer
    serializer_detail_class = VersionDetailSerializer
    pagination_class = DandiPagination

    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created']

    lookup_field = 'version'
    lookup_value_regex = Version.VERSION_REGEX

    def get_queryset(self):
        # We need to check the dandiset to see if it's embargoed, and if so whether or not the
        # user has ownership
        dandiset = get_object_or_404(Dandiset, pk=self.kwargs['dandiset__pk'])
        if dandiset.embargo_status != Dandiset.EmbargoStatus.OPEN:
            if not self.request.user.is_authenticated:
                # Clients must be authenticated to access it
                raise NotAuthenticated()
            if not self.request.user.has_perm('owner', dandiset):
                # The user does not have ownership permission
                raise PermissionDenied()
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
        responses={200: VersionDetailSerializer()},
    )
    @action(detail=True, methods=['GET'])
    def info(self, request, **kwargs):
        """Django serialization of a version."""
        version = self.get_object()
        serializer = VersionDetailSerializer(instance=version)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=VersionMetadataSerializer(),
        responses={200: VersionDetailSerializer()},
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

        serializer = VersionMetadataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data['name']
        metadata = serializer.validated_data['metadata']
        # Strip away any computed fields
        metadata = Version.strip_metadata(metadata)

        version.name = name
        version.metadata = metadata
        version.status = Version.Status.PENDING
        version.save()

        serializer = VersionDetailSerializer(instance=version)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=no_body,
        manual_parameters=[DANDISET_PK_PARAM, VERSION_PARAM],
        responses={200: VersionSerializer()},
    )
    @action(detail=True, methods=['POST'])
    @method_decorator(permission_required_or_403('owner', (Dandiset, 'pk', 'dandiset__pk')))
    def publish(self, request, **kwargs):
        """Publish a version."""
        old_version: Version = self.get_object()
        if old_version.version != 'draft':
            return Response(
                'Only draft versions can be published',
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        if (
            old_version.dandiset.zarr_archives.exists()
            or old_version.dandiset.embargoed_zarr_archives.exists()
        ):
            raise ValidationError('Cannot publish dandisets which contain zarrs')
        if not old_version.valid:
            return Response(
                'Dandiset metadata or asset metadata is not valid',
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            new_version = old_version.publish_version

            new_version.doi = doi.create_doi(new_version)

            new_version.save()
            # Bulk create the join table rows to optimize linking assets to new_version
            AssetVersions = Version.assets.through

            # Add a new many-to-many association directly to any already published assets
            already_published_assets = old_version.assets.filter(published=True)
            AssetVersions.objects.bulk_create(
                [
                    AssetVersions(asset_id=asset['id'], version_id=new_version.id)
                    for asset in already_published_assets.values('id')
                ]
            )

            # Publish any draft assets
            # Import here to avoid dependency cycle
            from dandiapi.api.models import Asset

            draft_assets = old_version.assets.filter(published=False).all()
            for draft_asset in draft_assets:
                draft_asset.publish()
            Asset.objects.bulk_update(draft_assets, ['metadata', 'published'])

            AssetVersions.objects.bulk_create(
                [
                    AssetVersions(asset_id=asset.id, version_id=new_version.id)
                    for asset in draft_assets
                ]
            )

            # Save again to recompute metadata, specifically assetsSummary
            new_version.save()

            # Set the version of the draft to PUBLISHED so that it cannot be publishd again without
            # being modified and revalidated
            old_version.status = Version.Status.PUBLISHED
            old_version.save()

            transaction.on_commit(lambda: write_manifest_files.delay(new_version.id))

            serializer = VersionSerializer(new_version)
            return Response(serializer.data, status=status.HTTP_200_OK)

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
        elif not request.user.is_superuser:
            return Response(
                'Cannot delete published versions',
                status=status.HTTP_403_FORBIDDEN,
            )
        else:
            doi = version.doi
            version.delete()
            if doi is not None:
                delete_doi_task.delay(doi)
            return Response(None, status=status.HTTP_204_NO_CONTENT)
