from django.core.validators import RegexValidator
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from guardian.utils import get_40x_or_None
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandiapi.api.models import Asset, AssetBlob, AssetMetadata, Version
from dandiapi.api.views.common import DandiPagination
from dandiapi.api.views.serializers import AssetDetailSerializer, AssetSerializer


class AssetRequestSerializer(serializers.Serializer):
    metadata = serializers.JSONField()
    sha256 = serializers.CharField(
        max_length=64, validators=[RegexValidator(f'^{AssetBlob.SHA256_REGEX}$')]
    )


class AssetFilter(filters.FilterSet):
    path = filters.CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Asset
        fields = ['path']


class AssetViewSet(NestedViewSetMixin, DetailSerializerMixin, ReadOnlyModelViewSet):
    queryset = Asset.objects.all()

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = AssetSerializer
    serializer_detail_class = AssetDetailSerializer
    pagination_class = DandiPagination

    lookup_field = 'uuid'
    lookup_value_regex = Asset.UUID_REGEX

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = AssetFilter

    @swagger_auto_schema(
        responses={
            200: 'The asset metadata.',
        },
    )
    def retrieve(self, request, versions__dandiset__pk, versions__version, uuid):
        asset = self.get_object()
        # TODO use http://localhost:8000 for local deployments
        download_url = 'https://api.dandiarchive.org' + reverse(
            'asset-download',
            kwargs={
                'versions__dandiset__pk': versions__dandiset__pk,
                'versions__version': versions__version,
                'uuid': uuid,
            },
        )

        blob_url = asset.blob.blob.url
        metadata = {
            **asset.metadata.metadata,
            'identifier': uuid,
            'contentUrl': [download_url, blob_url],
        }
        return Response(metadata, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=AssetRequestSerializer(),
        responses={
            200: AssetDetailSerializer(),
            404: 'If a blob with the given checksum has not been validated',
        },
    )
    # @permission_required_or_403('owner', (Dandiset, 'pk', 'version__dandiset__pk'))
    def create(self, request, versions__dandiset__pk, versions__version):
        version: Version = get_object_or_404(
            Version,
            dandiset=versions__dandiset__pk,
            version=versions__version,
        )

        # TODO @permission_required doesn't work on methods
        # https://github.com/django-guardian/django-guardian/issues/723
        response = get_40x_or_None(request, ['owner'], version.dandiset, return_403=True)
        if response:
            return response

        serializer = AssetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        asset_blob = get_object_or_404(AssetBlob, sha256=serializer.validated_data['sha256'])

        metadata = serializer.validated_data['metadata']
        if 'path' not in metadata:
            return Response('No path specified in metadata', status=404)
        path = metadata['path']
        asset_metadata, created = AssetMetadata.objects.get_or_create(metadata=metadata)
        if created:
            asset_metadata.save()

        if version.assets.filter(path=path, blob=asset_blob, metadata=asset_metadata).exists():
            return Response('Asset Already Exists', status=status.HTTP_400_BAD_REQUEST)

        asset = Asset(
            path=path,
            blob=asset_blob,
            metadata=asset_metadata,
        )
        asset.save()
        version.assets.add(asset)

        serializer = AssetDetailSerializer(instance=asset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=AssetRequestSerializer(),
        responses={200: AssetDetailSerializer()},
    )
    # @permission_required_or_403('owner', (Dandiset, 'pk', 'version__dandiset__pk'))
    def update(self, request, versions__dandiset__pk, versions__version, **kwargs):
        """Update the metadata of an asset."""
        old_asset = self.get_object()
        version = Version.objects.get(
            dandiset__pk=versions__dandiset__pk,
            version=versions__version,
        )

        # TODO @permission_required doesn't work on methods
        # https://github.com/django-guardian/django-guardian/issues/723
        response = get_40x_or_None(request, ['owner'], version.dandiset, return_403=True)
        if response:
            return response

        serializer = AssetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        asset_blob = get_object_or_404(AssetBlob, sha256=serializer.validated_data['sha256'])

        metadata = serializer.validated_data['metadata']
        if 'path' not in metadata:
            return Response('No path specified in metadata', status=404)
        path = metadata['path']
        asset_metadata, created = AssetMetadata.objects.get_or_create(metadata=metadata)
        if created:
            asset_metadata.save()

        if asset_metadata == old_asset.metadata and asset_blob == old_asset.blob:
            # No changes, don't create a new asset
            new_asset = old_asset
        else:
            # Mint a new Asset whenever blob or metadata are modified
            new_asset = Asset(
                path=path,
                blob=asset_blob,
                metadata=asset_metadata,
                previous=old_asset,
            )
            new_asset.save()

            # Replace the old asset with the new one
            version.assets.add(new_asset)
            version.assets.remove(old_asset)

        serializer = AssetDetailSerializer(instance=new_asset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # @permission_required_or_403('owner', (Dandiset, 'pk', 'version__dandiset__pk'))
    def destroy(self, request, versions__dandiset__pk, versions__version, **kwargs):
        asset = self.get_object()
        version = Version.objects.get(
            dandiset__pk=versions__dandiset__pk, version=versions__version
        )

        # TODO @permission_required doesn't work on methods
        # https://github.com/django-guardian/django-guardian/issues/723
        response = get_40x_or_None(request, ['owner'], version.dandiset, return_403=True)
        if response:
            return response

        version.assets.remove(asset)
        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        responses={
            200: None,  # This disables the auto-generated 200 response
            301: 'Redirect to object store',
        }
    )
    @action(detail=True, methods=['GET'])
    def download(self, request, **kwargs):
        """Return a redirect to the file download in the object store."""
        return HttpResponseRedirect(redirect_to=self.get_object().blob.blob.url)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('path_prefix', openapi.IN_QUERY, type=openapi.TYPE_STRING)
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_STRING),
            )
        },
    )
    @action(detail=False, methods=['GET'])
    def paths(self, request, **kwargs):
        """
        Return the unique files/directories that directly reside under the specified path.

        The specified path must be a folder; it either must end in a slash or
        (to refer to the root folder) must be the empty string.
        """
        path_prefix: str = self.request.query_params.get('path_prefix') or ''
        # Enforce trailing slash
        if path_prefix and path_prefix[-1] != '/':
            path_prefix = f'{path_prefix}/'
        qs = self.get_queryset().filter(path__startswith=path_prefix).values()

        return Response(Asset.get_path(path_prefix, qs))

    # TODO: add create to forge an asset from a validation
