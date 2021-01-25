from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http.response import HttpResponseBase
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from dandiapi.api.dandiset_migration import move_if_necessary
from dandiapi.api.models import Dandiset


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def map_ids_view(request: Request) -> HttpResponseBase:
    logs = []
    for dandiset in Dandiset.objects.all():
        logs += move_if_necessary(dandiset)
    return Response(logs)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def map_id_view(request: Request, dandiset_id) -> HttpResponseBase:
    dandiset = get_object_or_404(Dandiset, pk=dandiset_id)
    logs = move_if_necessary(dandiset)
    return Response(logs)
