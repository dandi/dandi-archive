from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from guardian.utils import get_40x_or_None
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandiapi.api.models import Asset, AssetBlob, AssetMetadata, Validation, Version
from dandiapi.api.views.common import DandiPagination
from dandiapi.api.views.serializers import (
    AssetDetailSerializer,
    AssetMetadataSerializer,
    AssetSerializer,
)


class CreateRequestSerializer(serializers.Serializer):
    metadata = serializers.JSONField()
    sha256 = serializers.CharField(trim_whitespace=False)

    def create(self, validated_data):
        return AssetMetadata(metadata=validated_data['metadata'])


class AssetFilter(filters.FilterSet):
    path = filters.CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Asset
        fields = ['path']


class AssetViewSet(NestedViewSetMixin, DetailSerializerMixin, ReadOnlyModelViewSet):
    queryset = Asset.objects.all().select_related('version')

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = AssetSerializer
    serializer_detail_class = AssetDetailSerializer
    pagination_class = DandiPagination

    lookup_field = 'blob__path'
    lookup_value_regex = r'\S+'

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = AssetFilter

    def get_object(self):
        """
        Return the object the view is displaying.

        Because blob__path is embedded in the API URL, handling the leading slash is confusing.
        Calling "/api/.../assets/foo/bar/baz.nwb" results in blob_path="foo/bar/baz.nwb",
        with no leading slash, which makes sense from a URL perspective, but is not a valid path.
        Calling "/api/.../assets//foo/bar/baz.nwb" results in blob_path="/foo/bar/baz.nwb",
        which is a valid path, but not a good URL. This is the URL generated when using swagger.
        This code prepends a slash if it isn't present, so either use case works as intended.
        Django already handles either raw or URL encoded '/', so that isn't a concern.
        """
        if self.kwargs['blob__path'][:1] != '/':
            self.kwargs['blob__path'] = f'/{self.kwargs["blob__path"]}'
        return super().get_object()

    @swagger_auto_schema(request_body=AssetMetadataSerializer())
    # @permission_required_or_403('owner', (Dandiset, 'pk', 'version__dandiset__pk'))
    def update(self, request, **kwargs):
        """Update the metadata of an asset."""
        asset = self.get_object()

        # TODO @permission_required doesn't work on methods
        # https://github.com/django-guardian/django-guardian/issues/723
        response = get_40x_or_None(request, ['owner'], asset.version.dandiset, return_403=True)
        if response:
            return response

        serializer = AssetMetadataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset_metadata = AssetMetadata.create_or_find(**serializer.validated_data)
        asset_metadata.save()

        asset.metadata = asset_metadata
        asset.save()

        serializer = AssetDetailSerializer(instance=asset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=CreateRequestSerializer())
    # @permission_required_or_403('owner', (Dandiset, 'pk', 'version__dandiset__pk'))
    def create(self, request, version__dandiset__pk, version__version):
        version: Version = get_object_or_404(
            Version,
            dandiset=version__dandiset__pk,
            version=version__version,
        )

        # TODO @permission_required doesn't work on methods
        # https://github.com/django-guardian/django-guardian/issues/723
        response = get_40x_or_None(request, ['owner'], version.dandiset, return_403=True)
        if response:
            return response

        serializer = CreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validation: Validation = get_object_or_404(
            Validation,
            sha256=serializer.validated_data['sha256'],
        )
        if validation.state != Validation.State.SUCCEEDED:
            raise ValidationError('Validation has not succeeded.')
        # TODO: Check that the validation is not too old

        asset_blob = AssetBlob.from_validation(validation)
        asset_metadata = serializer.save()
        asset = Asset(blob=asset_blob, metadata=asset_metadata, version=version)
        asset_blob.save()
        asset_metadata.save()
        asset.save()

        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['GET'])
    def download(self, request, **kwargs):
        """Return a redirect to the file download in the object store."""
        return HttpResponseRedirect(redirect_to=self.get_object().blob.url)

    @action(detail=False, methods=['GET'])
    def paths(self, request, **kwargs):
        """
        Return the unique files/directories that directly reside under the specified path.

        The specified path must be a folder (must end with a slash).
        """
        path_prefix: str = self.request.query_params.get('path_prefix') or '/'
        # Enforce trailing slash
        path_prefix = f'{path_prefix}/' if path_prefix[-1] != '/' else path_prefix
        qs = self.get_queryset().filter(path__startswith=path_prefix).values()

        return Response(Asset.get_path(path_prefix, qs))

    # TODO: add create to forge an asset from a validation
