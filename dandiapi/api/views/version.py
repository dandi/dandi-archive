from rest_framework import serializers
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandiapi.api.models import Version
from dandiapi.api.views.common import DandiPagination
from dandiapi.api.views.dandiset import DandisetSerializer


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = [
            'dandiset',
            'version',
            'name',
            'created',
            'modified',
            'assets_count',
            'size',
        ]
        read_only_fields = ['created']

    dandiset = DandisetSerializer()


class VersionDetailSerializer(VersionSerializer):
    class Meta(VersionSerializer.Meta):
        fields = VersionSerializer.Meta.fields + ['metadata']


class VersionViewSet(NestedViewSetMixin, DetailSerializerMixin, ReadOnlyModelViewSet):
    queryset = Version.objects.all().select_related('dandiset')
    queryset_detail = queryset

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = VersionSerializer
    serializer_detail_class = VersionDetailSerializer
    pagination_class = DandiPagination

    lookup_field = 'version'
    lookup_value_regex = Version.VERSION_REGEX
