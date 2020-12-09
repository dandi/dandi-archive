from __future__ import annotations

from django.contrib.auth.models import User
from django.http.response import HttpResponseBase
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response

from dandiapi.api.views.serializers import UserSerializer


@swagger_auto_schema(
    method='GET',
    query_serializer=UserSerializer,
    responses={200: UserSerializer(many=True)},
)
@api_view(['GET'])
@parser_classes([JSONParser])
def users_search_view(request: Request) -> HttpResponseBase:
    """Search for a user."""
    request_serializer = UserSerializer(data=request.query_params)
    request_serializer.is_valid(raise_exception=True)
    username: str = request_serializer.validated_data['username']

    options = User.objects.filter(username__startswith=username).order_by('username')[:10]

    response_serializer = UserSerializer(options, many=True)
    return Response(response_serializer.data)
