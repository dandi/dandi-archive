from __future__ import annotations

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseBase, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from drf_yasg.utils import swagger_auto_schema
from oauth2_provider.views.base import AuthorizationView
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from dandiapi.api.mail import send_new_user_message_email, send_registered_notice_email
from dandiapi.api.models import UserMetadata
from dandiapi.api.permissions import IsApproved
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
        'status': user.metadata.status,
        'created': user.date_joined,
    }


def social_account_to_dict(social_account: SocialAccount):
    """Serialize a social account to a dict."""
    user = social_account.user
    # This is a reasonable default if the attached GitHub account doesn't have a name
    name = f'{user.first_name} {user.last_name}'.strip()

    # We are assuming that login is a required field for GitHub users
    username = social_account.extra_data['login']
    name = social_account.extra_data.get('name') or name
    created = social_account.extra_data.get('created_at')

    return {
        'admin': user.is_superuser,
        'username': username,
        'name': name,
        'status': user.metadata.status,
        'created': created,
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
    request_serializer.is_valid(raise_exception=True)
    username: str = request_serializer.validated_data['username']

    # Perform a search, excluding any inactive users
    social_accounts = SocialAccount.objects.filter(
        extra_data__icontains=username,
        user__is_active=True,
        user__metadata__status=UserMetadata.Status.APPROVED,
    )[:10]
    users = [social_account_to_dict(social_account) for social_account in social_accounts]

    # Try searching Django's regular `User`s if there aren't any results.
    # This allows this feature to work in development without having to conditionalize
    # code based on the type of deployment.
    if not users:
        # Perform a search, excluding any user accounts that
        # are inactive + the default 'AnonymousUser' account
        users = [
            user_to_dict(user)
            for user in User.objects.filter(username__icontains=username).filter(
                ~Q(username='AnonymousUser'),
                is_active=True,
                metadata__status=UserMetadata.Status.APPROVED,
            )[:10]
        ]

    response_serializer = UserDetailSerializer(users, many=True)
    return Response(response_serializer.data)


@require_http_methods(['GET'])
def authorize_view(request: HttpRequest) -> HttpResponse:
    """Override authorization endpoint to handle user questionnaire."""
    user: User = request.user
    if (
        user.is_authenticated
        and not user.is_superuser
        and user.metadata.status == UserMetadata.Status.INCOMPLETE
    ):
        # send user to questionnaire if they haven't filled it out yet
        return HttpResponseRedirect(
            f'{reverse("user-questionnaire")}' f'?{request.META["QUERY_STRING"]}'
        )
    # otherwise, continue with normal authorization workflow
    return AuthorizationView.as_view()(request)


QUESTIONS = [
    'First Name',
    'Last Name',
    'What do you plan to use DANDI for?',
    'Please list any affiliations you have.',
]


@swagger_auto_schema()
@api_view(['GET', 'POST'])
@require_http_methods(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_questionnaire_form_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        user_metadata: UserMetadata = request.user.metadata
        questionnaire_already_filled_out = user_metadata.questionnaire_form is not None

        user_metadata.questionnaire_form = {}
        req_body = request.POST.dict()
        for question in QUESTIONS:
            user_metadata.questionnaire_form[question] = req_body.get(question)
        user_metadata.status = UserMetadata.Status.PENDING
        user_metadata.save()

        # Only send emails when the user fills out the questionnaire for the first time.
        # If they go back later and update it for whatever reason, they should not receive
        # another email confirming their registration.
        if not questionnaire_already_filled_out:
            # send email indicating the user has signed up
            for socialaccount in request.user.socialaccount_set.all():
                send_registered_notice_email(request.user, socialaccount)
                send_new_user_message_email(request.user, socialaccount)

        # pass on OAuth query string params to auth endpoint
        return HttpResponseRedirect(
            f'{reverse("authorize").rstrip("/")}/?{request.META["QUERY_STRING"]}'
        )
    return render(
        request,
        'api/account/questionnaire_form.html',
        {'questions': QUESTIONS, 'query_params': request.GET.dict()},
    )
