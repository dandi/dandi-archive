from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Dandiset, NWBFile, Subject
from .serializers import DandisetSerializer, DandisetPublishSerializer, NWBFileSerializer, SubjectSerializer
from .tasks import publish_dandiset


class PermissionMixin:
    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            permission_classes = []
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]


class DandisetPagination(PageNumberPagination):
    page_size = 25
    max_page_size = 100
    page_size_query_param = 'page_size'


class DandisetViewSet(PermissionMixin, viewsets.ModelViewSet):
    queryset = Dandiset.objects.all().order_by('id')
    serializer_class = DandisetSerializer
    pagination_class = DandisetPagination

    @action(detail=False, methods=['POST'])
    def publish(self, request, *args, **kwargs):
        serializer = DandisetPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(publish_dandiset.delay(**data).id)


class SubjectViewSet(PermissionMixin, viewsets.ModelViewSet):
    queryset = Subject.objects.all().order_by('id')
    serializer_class = SubjectSerializer
    pagination_class = DandisetPagination


class NWBFileViewSet(PermissionMixin, viewsets.ModelViewSet):
    queryset = NWBFile.objects.all().order_by('id')
    serializer_class = NWBFileSerializer
    pagination_class = DandisetPagination
