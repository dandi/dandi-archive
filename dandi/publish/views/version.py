from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandi.publish.models import Dandiset, Version
from dandi.publish.tasks import publish_version
from dandi.publish.views.common import DandiPagination
from dandi.publish.views.dandiset import DandisetSerializer


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
            # 'size',
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

    @action(detail=False, methods=['POST'])
    def publish(self, request, dandiset__pk):
        dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
        publish_version.delay(dandiset.id)
        return Response('', status=status.HTTP_202_ACCEPTED)
