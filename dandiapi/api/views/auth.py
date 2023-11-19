from __future__ import annotations

import json
from json.decoder import JSONDecodeError

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.http.response import Http404, HttpResponseBase, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from drf_yasg.utils import swagger_auto_schema
from oauth2_provider.views.base import AuthorizationView
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from dandiapi.api.mail import (
    send_approved_user_message,
    send_new_user_message_email,
    send_registered_notice_email,
)
from dandiapi.api.models import UserMetadata
from dandiapi.api.permissions import IsApproved


@swagger_auto_schema(
    methods=['GET', 'POST'],
    responses={200: 'The user token'},
)
@api_view(['GET', 'POST'])
@permission_classes([IsApproved])
def auth_token_view(request: Request) -> HttpResponseBase:
    if request.method == 'GET':
        token = get_object_or_404(Token, user=request.user)
    elif request.method == 'POST':
        Token.objects.filter(user=request.user).delete()
        token = Token.objects.create(user=request.user)
    return Response(token.key)


QUESTIONS = [
    {'question': 'First Name', 'max_length': 100},
    {'question': 'Last Name', 'max_length': 100},
    {'question': 'What do you plan to use DANDI for?', 'max_length': 1000},
    {'question': 'Please list any affiliations you have.', 'max_length': 1000},
]

# questions for new users
NEW_USER_QUESTIONS = QUESTIONS

# questions for existing users who have no first/last name
COLLECT_USER_NAME_QUESTIONS = QUESTIONS[:2]


@require_http_methods(['GET'])
def authorize_view(request: HttpRequest) -> HttpResponse:
    from django.contrib.sites.models import Site
#     raise Exception(Site.objects.get_current())
    """Override authorization endpoint to handle user questionnaire."""
    user: User = request.user
    if (
        user.is_authenticated
        and not user.is_superuser
        and user.metadata.status == UserMetadata.Status.INCOMPLETE
    ):
        # send user to questionnaire if they haven't filled it out yet
        return HttpResponseRedirect(
            f'{reverse("user-questionnaire")}'
            f'?{request.META["QUERY_STRING"]}&QUESTIONS={json.dumps(NEW_USER_QUESTIONS)}'
        )
    elif not user.is_anonymous and (not user.first_name or not user.last_name):
        # if this user doesn't have a first/last name available, redirect them to a
        # form to provide those before they can log in.
        return HttpResponseRedirect(
            f'{reverse("user-questionnaire")}'
            f'?{request.META["QUERY_STRING"]}&QUESTIONS={json.dumps(COLLECT_USER_NAME_QUESTIONS)}'
        )

    # otherwise, continue with normal authorization workflow
    return AuthorizationView.as_view()(request)


@swagger_auto_schema()
@api_view(['GET', 'POST'])
@require_http_methods(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def user_questionnaire_form_view(request: HttpRequest) -> HttpResponse:
    user: User = request.user
    if request.method == 'POST':
        user_metadata: UserMetadata = user.metadata
        questionnaire_already_filled_out = user_metadata.questionnaire_form is not None
        # we can't use Django forms here because we're using a JSONField, so we have
        # to extract the request data manually
        req_body = request.POST.dict()
        user_metadata.questionnaire_form = {
            question['question']: req_body.get(question['question'])[: question['max_length']]
            if req_body.get(question['question']) is not None
            else None
            for question in QUESTIONS
        }
        user_metadata.save(update_fields=['questionnaire_form'])

        # Save first and last name if applicable
        if 'First Name' in req_body and req_body['First Name']:
            user.first_name = req_body['First Name']
            user.save(update_fields=['first_name'])
        if 'Last Name' in req_body and req_body['Last Name']:
            user.last_name = req_body['Last Name']
            user.save(update_fields=['last_name'])

#         Only send emails when the user fills out the questionnaire for the first time.
#         If they go back later and update it for whatever reason, they should not receive
#         another email confirming their registration. Additionally, users who have already
#         been approved that go back and update the form later should also not receive an email.
        if (
            not questionnaire_already_filled_out
            and user_metadata.status == UserMetadata.Status.INCOMPLETE
        ):
            is_edu_email: bool = user.email.endswith('.edu')

            # auto-approve users with edu emails, otherwise require manual approval
            user_metadata.status = (
                UserMetadata.Status.APPROVED if is_edu_email else UserMetadata.Status.PENDING
            )
            user_metadata.save(update_fields=['status'])

            # send email indicating the user has signed up
#             for socialaccount in user.socialaccount_set.all():
#                 # Send approved email if they have been auto-approved
#                 if user_metadata.status == UserMetadata.Status.APPROVED:
#                     send_approved_user_message(user, socialaccount)
#                 # otherwise, send "awaiting approval" email
#                 else:
#                     send_registered_notice_email(user, socialaccount)
#                     send_new_user_message_email(user, socialaccount)

        # pass on OAuth query string params to auth endpoint
#         import logging
#         x = f'{reverse("authorize").rstrip("/")}/?{request.META["QUERY_STRING"]}'
#         logging.info('Blob with ETag %s does not yet exist', request.method)
        return HttpResponseRedirect(
            f'{reverse("authorize").rstrip("/")}/?{request.META["QUERY_STRING"]}'
        )

    try:
        # questions to display in the form
        questions = json.loads(request.GET.get('QUESTIONS'))
    except (JSONDecodeError, TypeError):
        raise Http404

    return render(
        request,
        'api/account/questionnaire_form.html',
        {
            'questions': questions,
            'query_params': request.GET.dict(),
            'dandi_web_app_url': settings.DANDI_WEB_APP_URL,
        },
    )
