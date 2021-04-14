from __future__ import annotations

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.http.response import HttpResponseBase
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from dandiapi.api.views.serializers import UserDetailSerializer, UserSerializer


def user_to_dict(user: User):
    """
    Serialize a user to a dict.

    This exists only as a fallback in case a user doesn't have a social account.
    """
    return {
        'admin': user.is_superuser,
        'username': user.username,
        'name': f'{user.first_name} {user.last_name}'.strip(),
    }


def social_account_to_dict(social_account: SocialAccount):
    """Serialize a social account to a dict."""
    user = social_account.user
    # This is a reasonable default if the attached GitHub account doesn't have a name
    name = f'{user.first_name} {user.last_name}'.strip()

    # We are assuming that login is a required field for GitHub users
    username = social_account.extra_data['login']
    name = social_account.extra_data.get('name') or name

    return {
        'admin': user.is_superuser,
        'username': username,
        'name': name,
    }


@swagger_auto_schema(
    method='GET',
    responses={200: UserDetailSerializer},
)
@api_view(['GET'])
@parser_classes([JSONParser])
@permission_classes([IsAuthenticated])
def users_me_view(request: Request) -> HttpResponseBase:
    """Get the currently authenticated user."""
    if request.user.socialaccount_set.count() == 1:
        social_account = request.user.socialaccount_set.get()
        user_dict = social_account_to_dict(social_account)
    else:
        user_dict = user_to_dict(request.user)
    response_serializer = UserDetailSerializer(user_dict)
    return Response(response_serializer.data)


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

    social_accounts = SocialAccount.objects.filter(extra_data__icontains=username)[:10]
    users = [social_account_to_dict(social_account) for social_account in social_accounts]

    response_serializer = UserDetailSerializer(users, many=True)
    return Response(response_serializer.data)
