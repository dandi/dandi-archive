from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models.functions import Cast

from .models import Dandiset, NWBFile
from .serializers import DandisetSerializer, DandisetListSerializer, DandisetPublishSerializer, NWBFileSerializer
from .tasks import publish_dandiset


class DandisetPagination(PageNumberPagination):
    page_size = 25
    max_page_size = 100
    page_size_query_param = 'page_size'


class DandisetViewSet(viewsets.ModelViewSet):
    queryset = Dandiset.objects.all()\
        .order_by('dandi_id', '-version')\
        .distinct('dandi_id')
    serializer_class = DandisetListSerializer
    pagination_class = DandisetPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'dandi_id'

    @action(detail=False, methods=['POST'])
    def publish(self, request, *args, **kwargs):
        serializer = DandisetPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(publish_dandiset.delay(**data).id)

    @action(detail=True, methods=['GET'], url_path='(?P<version>[^/]+)')
    def version(self, request, dandi_id, version):
        queryset = self.filter_queryset(self.get_queryset())
        filter_kwargs = {'dandi_id': dandi_id, 'version': version}
        obj = get_object_or_404(queryset, **filter_kwargs)
        serializer = DandisetSerializer(obj)
        return Response(serializer.data)

    @action(detail=False)
    def search(self, request, *args, **kwargs):
        query = request.GET.get('search')
        if not query:
            # return a listing of everything if there is no query
            return self.list(request)
        queryset = Dandiset.objects\
            .annotate(metadata_text=Cast('metadata', models.TextField()))\
            .filter(metadata_text__search=query)\
            .order_by('dandi_id', '-version')\
            .distinct('dandi_id')
        serializer = DandisetListSerializer(queryset, many=True)
        return Response(serializer.data)
