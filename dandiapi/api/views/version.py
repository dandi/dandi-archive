from django.utils.decorators import method_decorator
from drf_yasg.utils import no_body, swagger_auto_schema
from guardian.decorators import permission_required_or_403
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandiapi.api import doi
from dandiapi.api.models import Dandiset, Version, VersionMetadata
from dandiapi.api.tasks import validate_version_metadata, write_yamls
from dandiapi.api.views.common import DandiPagination
from dandiapi.api.views.serializers import (
    VersionDetailSerializer,
    VersionMetadataSerializer,
    VersionSerializer,
)


class VersionViewSet(NestedViewSetMixin, DetailSerializerMixin, ReadOnlyModelViewSet):
    queryset = Version.objects.all().select_related('dandiset').order_by('created')
    queryset_detail = queryset

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = VersionSerializer
    serializer_detail_class = VersionDetailSerializer
    pagination_class = DandiPagination

    lookup_field = 'version'
    lookup_value_regex = Version.VERSION_REGEX

    @swagger_auto_schema(
        responses={
            200: 'The version metadata.',
        },
    )
    def retrieve(self, request, **kwargs):
        version = self.get_object()
        return Response(version.metadata.metadata, status=status.HTTP_200_OK)

    # TODO clean up this action
    # Originally retrieve() returned this, but the API specification was modified so that
    # retrieve() only returns the metadata for a version, instead of a serialization.
    # Unfortunately the web UI is built around VersionDetailSerializer, so this endpoint was
    # added to avoid rewriting the web UI.
    @swagger_auto_schema(
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

        version_metadata: VersionMetadata
        version_metadata, created = VersionMetadata.objects.get_or_create(
            name=name,
            metadata=metadata,
        )

        if created:
            version_metadata.save()

        version.metadata = version_metadata
        version.save()

        validate_version_metadata.delay(version.id)

        serializer = VersionDetailSerializer(instance=version)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=no_body, responses={200: VersionSerializer()})
    @action(detail=True, methods=['POST'])
    @method_decorator(permission_required_or_403('owner', (Dandiset, 'pk', 'dandiset__pk')))
    def publish(self, request, **kwargs):
        # TODO remove this check once publish is allowed
        if not request.user.is_superuser:
            return Response('Must be an admin to publish', status=status.HTTP_403_FORBIDDEN)

        old_version: Version = self.get_object()
        if old_version.version != 'draft':
            return Response(
                'Only draft versions can be published',
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        if not old_version.valid:
            return Response(
                'Dandiset metadata or asset metadata is not valid',
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_version = old_version.publish_version

        new_version.doi = doi.create_doi(new_version)

        new_version.save()
        # Bulk create the join table rows to optimize linking assets to new_version
        AssetVersions = Version.assets.through  # noqa: N806

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
        new_published_assets = [Asset.published_asset(draft_asset) for draft_asset in draft_assets]
        Asset.objects.bulk_create(new_published_assets)

        AssetVersions.objects.bulk_create(
            [
                AssetVersions(asset_id=asset.id, version_id=new_version.id)
                for asset in new_published_assets
            ]
        )

        write_yamls.delay(new_version.id)

        serializer = VersionSerializer(new_version)
        return Response(serializer.data, status=status.HTTP_200_OK)
