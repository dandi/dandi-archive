from django.http import HttpResponseRedirect
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from publish.models import Asset
from publish.views.common import DandiPagination
from publish.views.version import VersionSerializer


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'version',
            'uuid',
            'path',
            'size',
            'sha256',
            'created',
            'updated',
        ]
        read_only_fields = ['created']

    version = VersionSerializer()


class AssetDetailSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        fields = AssetSerializer.Meta.fields + ['metadata']


class AssetFilter(filters.FilterSet):
    path = filters.CharFilter(lookup_expr='exact', field_name='path')

    class Meta:
        model = Asset
        fields = ['path']


class AssetViewSet(NestedViewSetMixin, DetailSerializerMixin, ReadOnlyModelViewSet):
    queryset = Asset.objects.all().select_related('version__dandiset')
    queryset_detail = queryset

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = AssetSerializer
    serializer_detail_class = AssetDetailSerializer
    pagination_class = DandiPagination

    lookup_field = 'uuid'
    lookup_value_regex = Asset.UUID_REGEX

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = AssetFilter

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

        # Enfore trailing slash
        path_prefix = f'{path_prefix}/' if path_prefix[-1] != '/' else path_prefix
        prefix_parts = [part for part in path_prefix.split('/') if part]

        qs = self.get_queryset().filter(path__startswith=path_prefix).values()

        paths = set()
        for asset in qs:
            path_parts = [part for part in asset['path'].split('/') if part]

            # Pivot index is -1 (include all path parts) if prefix is '/'
            pivot_index = path_parts.index(prefix_parts[-1]) if len(prefix_parts) else -1
            base_path, *remainder = path_parts[pivot_index + 1 :]
            paths.add(f'{base_path}/' if len(remainder) else base_path)

        return Response(sorted(paths))
