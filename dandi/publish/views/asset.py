from django.http import HttpResponseRedirect
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin

from dandi.publish.models import Asset
from dandi.publish.views.common import DandiPagination
from dandi.publish.views.version import VersionSerializer


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
            'modified',
            'metadata',
        ]
        read_only_fields = ['created']

    version = VersionSerializer()


class AssetFilter(filters.FilterSet):
    path = filters.CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Asset
        fields = ['path']


class AssetViewSet(NestedViewSetMixin, ReadOnlyModelViewSet):
    queryset = Asset.objects.all().select_related('version__dandiset')

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = AssetSerializer
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
        # Enforce trailing slash
        path_prefix = f'{path_prefix}/' if path_prefix[-1] != '/' else path_prefix
        qs = self.get_queryset().filter(path__startswith=path_prefix).values()

        return Response(Asset.get_path(path_prefix, qs))
