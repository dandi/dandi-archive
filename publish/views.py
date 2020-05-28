from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin


from .models import Asset, Dandiset, Version
from .serializers import (
    AssetDetailSerializer,
    AssetSerializer,
    DandisetSerializer,
    VersionDetailSerializer,
    VersionSerializer,
)
from .tasks import publish_version, sync_dandiset


class DandiPagination(PageNumberPagination):
    page_size = 25
    max_page_size = 100
    page_size_query_param = 'page_size'


class DandisetViewSet(ReadOnlyModelViewSet):
    queryset = Dandiset.objects.all()

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = DandisetSerializer
    pagination_class = DandiPagination

    lookup_value_regex = Dandiset.IDENTIFIER_REGEX
    # This is not strictly necessary (it defaults to 'pk'), but it clarifies
    # that the 'identifier' property should be used when forming URLs
    # TODO: Test how reverse URLs are created
    lookup_url_kwarg = 'identifier'

    def get_object(self):
        # Alternative to path converters, which DRF doesn't support
        # https://docs.djangoproject.com/en/3.0/topics/http/urls/#registering-custom-path-converters

        lookup_url = self.kwargs[self.lookup_url_kwarg]
        try:
            lookup_value = int(lookup_url)
        except ValueError:
            raise Http404('Not a valid identifier.')
        self.kwargs[self.lookup_url_kwarg] = lookup_value

        return super().get_object()

    @action(detail=False, methods=['POST'])
    def sync(self, request):
        if 'folder-id' not in request.query_params:
            raise APIException(
                detail='Missing query parameter "folder-id"', code=status.HTTP_400_BAD_REQUEST
            )
        draft_folder_id = request.query_params['folder-id']

        sync_dandiset.delay(draft_folder_id)


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


class AssetViewSet(NestedViewSetMixin, DetailSerializerMixin, ReadOnlyModelViewSet):
    queryset = Asset.objects.all().select_related('version__dandiset')
    queryset_detail = queryset

    # permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = AssetSerializer
    serializer_detail_class = AssetDetailSerializer
    pagination_class = DandiPagination

    lookup_field = 'uuid'
    lookup_value_regex = Asset.UUID_REGEX
