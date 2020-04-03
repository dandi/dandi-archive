from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

from .models import Dandiset, NWBFile, Subject
from .serializers import DandisetSerializer, NWBFileSerializer, SubjectSerializer


class DandisetPagination(PageNumberPagination):
    page_size = 25
    max_page_size = 100
    page_size_query_param = 'page_size'


class DandisetViewSet(viewsets.ModelViewSet):
    queryset = Dandiset.objects.all().order_by('id')
    serializer_class = DandisetSerializer
    pagination_class = DandisetPagination


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all().order_by('id')
    serializer_class = SubjectSerializer
    pagination_class = DandisetPagination


class NWBFileViewSet(viewsets.ModelViewSet):
    queryset = NWBFile.objects.all().order_by('id')
    serializer_class = NWBFileSerializer
    pagination_class = DandisetPagination
