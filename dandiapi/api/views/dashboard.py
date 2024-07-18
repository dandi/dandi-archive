from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Exists, OuterRef
from django.http import HttpRequest, HttpResponseRedirect, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django.views.generic.base import TemplateView

from dandiapi.api.mail import send_approved_user_message, send_rejected_user_message
from dandiapi.api.models import Asset, AssetBlob, Upload, UserMetadata, Version
from dandiapi.api.views.users import social_account_to_dict

if TYPE_CHECKING:
    from allauth.socialaccount.models import SocialAccount


class DashboardMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class DashboardView(DashboardMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['orphaned_asset_count'] = self._orphaned_asset_count()
        context['orphaned_asset_blob_count'] = self._orphaned_asset_blob_count()
        non_valid_assets = self._non_valid_assets()
        context['non_valid_asset_count'] = non_valid_assets.count()
        context['non_valid_assets'] = non_valid_assets[:10]
        uploads = self._uploads()
        context['upload_count'] = uploads.count()
        context['uploads'] = uploads[:10]
        users = self._users()
        context['user_count'] = users.count()
        context['users'] = users

        return context

    def _orphaned_asset_count(self):
        return (
            Asset.objects.annotate(
                has_version=Exists(Version.objects.filter(assets=OuterRef('id')))
            )
            .filter(has_version=False)
            .count()
        )

    def _orphaned_asset_blob_count(self):
        return (
            AssetBlob.objects.annotate(
                has_asset=Exists(Asset.objects.filter(blob_id=OuterRef('id')))
            )
            .filter(has_asset=False)
            .count()
        )

    def _non_valid_assets(self):
        return (
            Asset.objects.prefetch_related('versions__dandiset')
            .select_related('zarr')
            .annotate(has_version=Exists(Version.objects.filter(assets=OuterRef('id'))))
            .filter(has_version=True)
            .exclude(status=Asset.Status.VALID)
        )

    def _uploads(self):
        return Upload.objects.annotate()

    def _users(self):
        return (
            User.objects.select_related('metadata')
            .filter(metadata__status=UserMetadata.Status.APPROVED)
            .order_by('-date_joined')
        )


def mailchimp_csv_view(request: HttpRequest) -> StreamingHttpResponse:
    """Generate a Mailchimp-compatible CSV file of all active users."""
    # In production, there's a placeholder user with a blank email that we want
    # to avoid.
    users = User.objects.filter(metadata__status=UserMetadata.Status.APPROVED).exclude(email='')

    fieldnames = ['email', 'first_name', 'last_name']
    data = users.values(*fieldnames).iterator()

    def streaming_output() -> Iterator[str]:
        """A generator that "streams" CSV rows using a pseudo-buffer."""

        # This class implements a filelike's write() interface to provide a way
        # for the CSV writer to "return" the CSV lines as strings.
        class Echo:
            def write(self, value):
                return value

        # Yield back the rows of the CSV file.
        writer = csv.DictWriter(Echo(), fieldnames=fieldnames)
        yield writer.writeheader()
        for row in data:
            yield writer.writerow(row)

    response = StreamingHttpResponse(
        streaming_output(),
        content_type='text/plain',
        headers={
            'Content-Disposition': 'attachment; filename="dandi_users_mailchimp.csv"',
        },
    )

    return response


@require_http_methods(['GET', 'POST'])
def user_approval_view(request: HttpRequest, username: str):
    # Redirect user to login if they're not authenticated
    if not request.user.is_authenticated:
        return HttpResponseRedirect(redirect_to=f'{settings.LOGIN_URL}?next={request.path}')

    # If they are authenticated but are not a superuser, deny access
    if not request.user.is_superuser:
        raise PermissionDenied

    user: User = get_object_or_404(User.objects.select_related('metadata'), username=username)
    social_account: SocialAccount = user.socialaccount_set.first()

    if request.method == 'POST':
        req_body = request.POST.dict()
        status = req_body.get('status')

        if status == UserMetadata.Status.REJECTED and not req_body.get('rejection_reason'):
            raise ValidationError('A rejection reason must be provided to reject a user.')

        user.metadata.status = status
        if req_body.get('rejection_reason') is not None:
            user.metadata.rejection_reason = req_body.get('rejection_reason')
        user.metadata.save()

        if user.metadata.status == UserMetadata.Status.APPROVED:
            send_approved_user_message(user, social_account)
            user.is_active = True
        elif user.metadata.status == UserMetadata.Status.REJECTED:
            send_rejected_user_message(user, social_account)
            user.is_active = False

        user.save()

    return render(
        request,
        'dashboard/user_approval.html',
        {
            'user': user,
            'social_account': social_account_to_dict(social_account)
            if social_account is not None
            else None,
        },
    )
