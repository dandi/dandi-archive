from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.core import mail
from django.db.models import OuterRef, Q, Subquery
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dandiapi.api.mail import build_message
from dandiapi.api.models import UserMetadata
from dandiapi.api.permissions import IsApproved
from dandiapi.api.views.serializers import UserDetailSerializer, UserEmailSerializer, UserSerializer

if TYPE_CHECKING:
    from django.http.response import HttpResponseBase
    from rest_framework.request import Request

logger = logging.getLogger(__name__)


def _get_user_status(user: User):
    try:
        return user.metadata.status
    except UserMetadata.DoesNotExist:
        return UserMetadata.Status.INCOMPLETE.value


def user_to_dict(user: User):
    """
    Serialize a user to a dict.

    This exists only as a fallback in case a user doesn't have a social account.
    """
    return {
        'admin': user.is_superuser,
        'username': user.username,
        'name': f'{user.first_name} {user.last_name}'.strip(),
        'status': _get_user_status(user),
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
        'status': _get_user_status(user),
    }


def serialize_user(user: User):
    """Serialize a user that's been annotated with a `social_account_data` field."""
    username = user.username
    name = f'{user.first_name} {user.last_name}'.strip()

    # Prefer social account info if present
    if user.social_account_data is not None:
        username = user.social_account_data.get('login', username)
        name = user.social_account_data.get('name', name)

    return {
        'admin': user.is_superuser,
        'username': username,
        'name': name,
        'status': _get_user_status(user),
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
@permission_classes([IsApproved])
def users_search_view(request: Request) -> HttpResponseBase:
    """Search for a user."""
    request_serializer = UserSerializer(data=request.query_params)

    # Swallow validation errors in the input string, and just send back null
    # results.
    if not request_serializer.is_valid(raise_exception=False):
        return Response([])

    username: str = request_serializer.validated_data['username']

    # Perform a search, excluding any inactive users and the 'AnonymousUser' account
    qs = (
        User.objects.select_related('metadata')
        .annotate(
            social_account_data=Subquery(
                SocialAccount.objects.filter(user=OuterRef('pk')).values('extra_data')
            )
        )
        .exclude(username='AnonymousUser')
        .filter(
            is_active=True,
            metadata__status=UserMetadata.Status.APPROVED,
        )
        .filter(
            Q(first_name__icontains=username)
            | Q(last_name__icontains=username)
            | Q(username__icontains=username)
            # `extra_data` isn't an actual JSON field so we need to search this way
            | Q(socialaccount__extra_data__iregex=rf'"login": "[^"]*{re.escape(username)}[^"]*"')
        )
        .order_by('date_joined')
    )[:10]

    users = [serialize_user(user) for user in qs]
    response_serializer = UserDetailSerializer(users, many=True)
    return Response(response_serializer.data)

@swagger_auto_schema(
    method='POST',
    operation_summary='Send an email to the specified user',
    request_body=UserEmailSerializer,
    responses={200: UserEmailSerializer},
)
@parser_classes([JSONParser])
@api_view(['POST'])
# @permission_classes([IsAdmin])  # TODO no such thing. try api/views/dashboard.py for mixin?
def user_email_view(request: Request) -> HttpResponseBase:
    request_serializer = UserEmailSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    message = build_message(
        subject=request_serializer.validated_data["subject"],
        message=request_serializer.validated_data["message"],
        to=[request_serializer.validated_data["username"]],
    )
    # TODO enable
    # with mail.get_connection() as connection:
    #     connection.send_messages([message])
    # TODO maybe should be a 301 or something?
    return Response(request_serializer.data)
