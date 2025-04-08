from __future__ import annotations

import datetime
import logging
import uuid
from typing import TYPE_CHECKING

from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from dandiapi.api.mail import send_approved_user_message
from dandiapi.api.models import UserMetadata

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.http.response import HttpResponseBase

logger = logging.getLogger(__name__)

# Time constants
TOKEN_EXPIRATION_SECONDS = 86400  # 24 hours


@require_http_methods(['GET'])
def verify_email_view(request: HttpRequest) -> HttpResponseBase:
    """Handle email verification from the verification link."""
    token_str = request.GET.get('token')

    if not token_str:
        return HttpResponseBadRequest('Missing verification token')

    try:
        token = uuid.UUID(token_str)
    except ValueError:
        return HttpResponseBadRequest('Invalid verification token format')

    try:
        user_metadata = UserMetadata.objects.get(verification_token=token)
    except UserMetadata.DoesNotExist:
        return HttpResponseBadRequest('Invalid or expired verification token')

    # Check if token is expired (24 hours)
    if user_metadata.verification_token_created:
        created_time = user_metadata.verification_token_created
        token_age = datetime.datetime.now(tz=datetime.UTC) - created_time
        if token_age.total_seconds() > TOKEN_EXPIRATION_SECONDS:
            return HttpResponseBadRequest('Verification token has expired')

    # Mark email as verified and approve user
    user_metadata.is_email_verified = True
    user_metadata.status = UserMetadata.Status.APPROVED
    user_metadata.save(update_fields=['is_email_verified', 'status'])

    # Send approval email
    user = user_metadata.user
    for socialaccount in user.socialaccount_set.all():
        send_approved_user_message(user, socialaccount)
        break  # Just send to the first social account

    logger.info('User %s email verified and approved', user.username)

    # Redirect to web app
    return redirect(reverse('authorize'))
