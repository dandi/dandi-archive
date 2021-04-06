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
from dandiapi.api.tasks import write_yamls
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
        request_body=VersionMetadataSerializer(),
        responses={200: VersionDetailSerializer()},
    )
    @method_decorator(permission_required_or_403('owner', (Dandiset, 'pk', 'dandiset__pk')))
    def update(self, request, **kwargs):
        """Update the metadata of a version."""
        version: Version = self.get_object()

        serializer = VersionMetadataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        version_metadata: VersionMetadata
        version_metadata, created = VersionMetadata.objects.get_or_create(
            name=serializer.validated_data['name'], metadata=serializer.validated_data['metadata']
        )

        if created:
            version_metadata.save()

        version.metadata = version_metadata
        version.save()

        serializer = VersionDetailSerializer(instance=version)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=no_body, responses={200: VersionSerializer()})
    @action(detail=True, methods=['POST'])
    @method_decorator(permission_required_or_403('owner', (Dandiset, 'pk', 'dandiset__pk')))
    def publish(self, request, **kwargs):
        # TODO remove this check once publish is allowed
        if not request.user.is_superuser:
            return Response('Must be an admin to publish', status=status.HTTP_403_FORBIDDEN)

        old_version = self.get_object()
        if old_version.version != 'draft':
            return Response(
                'Only draft versions can be published',
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        new_version = Version.copy(old_version)

        new_version.doi = doi.create_doi(new_version)

        new_version.save()
        # Bulk create the join table rows to optimize linking assets to new_version
        AssetVersions = Version.assets.through  # noqa: N806
        AssetVersions.objects.bulk_create(
            [
                AssetVersions(asset_id=asset['id'], version_id=new_version.id)
                for asset in old_version.assets.values('id')
            ]
        )

        write_yamls.delay(new_version.id)

        serializer = VersionSerializer(new_version)
        return Response(serializer.data, status=status.HTTP_200_OK)
