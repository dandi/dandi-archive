from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin


from publish.models import Dandiset, Version
from publish.serializers import (
    VersionDetailSerializer,
    VersionSerializer,
)
from publish.tasks import publish_version
from publish.views.common import DandiPagination


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
    def publish(self, request, parent_lookup_dandiset__pk):
        # TODO: parent_lookup_dandiset__pk is a string with leading stuff....
        dandiset = get_object_or_404(Dandiset, pk=parent_lookup_dandiset__pk)
        publish_version.delay(dandiset.id)
        return Response('', status=status.HTTP_202_ACCEPTED)
