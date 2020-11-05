from drf_yasg.utils import swagger_auto_schema
from guardian.utils import get_40x_or_None
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandiapi.api.models import Asset, Version, VersionMetadata
from dandiapi.api.views.common import DandiPagination
from dandiapi.api.views.serializers import (
    VersionDetailSerializer,
    VersionMetadataSerializer,
    VersionSerializer,
)


class VersionViewSet(NestedViewSetMixin, DetailSerializerMixin, ReadOnlyModelViewSet):
    queryset = Version.objects.all().select_related('dandiset')
    queryset_detail = queryset

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = VersionSerializer
    serializer_detail_class = VersionDetailSerializer
    pagination_class = DandiPagination

    lookup_field = 'version'
    lookup_value_regex = Version.VERSION_REGEX

    @swagger_auto_schema(request_body=VersionMetadataSerializer())
    # @permission_required_or_403('owner', (Dandiset, 'pk', 'dandiset__pk'))
    def update(self, request, **kwargs):
        """Update the metadata of a version."""
        version = self.get_object()

        # TODO @permission_required doesn't work on methods
        # https://github.com/django-guardian/django-guardian/issues/723
        response = get_40x_or_None(request, ['owner'], version.dandiset, return_403=True)
        if response:
            return response

        print(VersionMetadata.objects.all())
        print(request.data)
        serializer = VersionMetadataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version_metadata = VersionMetadata.create_or_find(**serializer.validated_data)
        version_metadata.save()

        version.metadata = version_metadata
        version.save()

        serializer = VersionDetailSerializer(instance=version)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], serializer_class=None)
    # @permission_required_or_403('owner', (Dandiset, 'pk', 'dandiset__pk'))
    def publish(self, request, **kwargs):
        old_version = self.get_object()

        # TODO @permission_required doesn't work on methods
        # https://github.com/django-guardian/django-guardian/issues/723
        response = get_40x_or_None(request, ['owner'], old_version.dandiset, return_403=True)
        if response:
            return response

        new_version = Version.copy(old_version)
        new_version.save()
        for old_asset in old_version.assets.all():
            new_asset = Asset.copy(old_asset, new_version)
            new_asset.save()
        serializer = VersionSerializer(new_version)
        return Response(serializer.data, status=status.HTTP_200_OK)
