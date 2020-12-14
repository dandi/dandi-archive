from __future__ import annotations

from django.contrib.auth.models import User
from django.forms.models import model_to_dict
from django.http.response import HttpResponseBase
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from dandiapi.api.views.serializers import UserDetailSerializer, UserSerializer


@swagger_auto_schema(
    method='GET',
    query_serializer=UserSerializer,
    responses={200: UserDetailSerializer(many=True)},
)
@api_view(['GET'])
@parser_classes([JSONParser])
@permission_classes([IsAuthenticated])
def users_search_view(request: Request) -> HttpResponseBase:
    """Search for a user."""
    request_serializer = UserSerializer(data=request.query_params)
    request_serializer.is_valid(raise_exception=True)
    username: str = request_serializer.validated_data['username']

    results = User.objects.filter(username__startswith=username).order_by('username')[:10]
    dict_results = [{'admin': user.is_superuser, **model_to_dict(user)} for user in results]

    response_serializer = UserDetailSerializer(dict_results, many=True)
    return Response(response_serializer.data)
