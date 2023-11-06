import csv

from allauth.socialaccount.models import SocialAccount
from django.contrib import admin, messages
from django.contrib.admin.options import TabularInline
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models.aggregates import Count
from django.db.models.query import Prefetch, QuerySet
from django.forms.models import BaseInlineFormSet
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from guardian.admin import GuardedModelAdmin

from dandiapi.api.models import (
    Asset,
    AssetBlob,
    Dandiset,
    EmbargoedAssetBlob,
    Upload,
    UserMetadata,
    Version,
)
from dandiapi.api.views.users import social_account_to_dict
from dandiapi.zarr.tasks import ingest_dandiset_zarrs

admin.site.site_header = 'DANDI Admin'
admin.site.site_title = 'DANDI Admin'


class UserMetadataInline(TabularInline):
    model = UserMetadata
    fields = ['status', 'questionnaire_form', 'rejection_reason']


class SocialAccountInline(TabularInline):
    model = SocialAccount


class UserAdmin(BaseUserAdmin):
    list_select_related = ['metadata']
    list_display = ['email', 'first_name', 'last_name', 'github_username', 'status', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    inlines = (
        UserMetadataInline,
        SocialAccountInline,
    )
    actions = ['export_emails_to_plaintext']
    list_filter = ['metadata__status', 'is_staff', 'is_superuser', 'is_active']

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                Prefetch('socialaccount_set', queryset=SocialAccount.objects.order_by('id'))
            )
        )

    @admin.action(description="Export selected users\' emails")
    def export_emails_to_plaintext(self, request, queryset):
        response = HttpResponse(content_type='text/plain')
        writer = csv.writer(response)
        emails = [obj.email for obj in queryset]
        writer.writerow(emails)
        return response

    @admin.display(ordering='metadata__status')
    def status(self, obj):
        return mark_safe(
            f'<a href="{reverse("user-approval", args=[obj.username])}">{obj.metadata.status}</a>'
        )

    @admin.display()
    def github_username(self, obj):
        social_account = obj.socialaccount_set.first()
        if social_account is None:
            return '(none)'
        gh_username: str = social_account_to_dict(social_account)['username']
        return mark_safe(f'<a href="https://github.com/{gh_username}">{gh_username}</a>')


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class LimitedFormset(BaseInlineFormSet):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs[:10]


class LimitedTabularInline(TabularInline):
    formset = LimitedFormset


class VersionInline(LimitedTabularInline):
    model = Version
    fields = ['version', 'name', 'status']


@admin.register(Dandiset)
class DandisetAdmin(GuardedModelAdmin):
    list_display = ['identifier', 'modified', 'created']
    readonly_fields = ['identifier', 'created']
    inlines = (VersionInline,)

    @admin.action(description='Ingest selected dandiset zarr archives')
    def ingest_dandiset_zarrs(self, request, queryset):
        for dandiset in queryset:
            ingest_dandiset_zarrs(dandiset_id=dandiset.id)

        # Return message
        plural = 's' if queryset.count() > 1 else ''
        self.message_user(
            request,
            f'Ingesting zarr archives for {queryset.count()} dandiset{plural}.',
            messages.SUCCESS,
        )

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.actions += ('ingest_dandiset_zarrs',)


class VersionStatusFilter(admin.SimpleListFilter):
    title = 'status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        for status in qs.values_list('status', flat=True).distinct():
            count = qs.filter(status=status).count()
            if count:
                yield (status, f'{status} ({count})')

    def queryset(self, request, queryset):
        status = self.value()
        if status:
            return queryset.filter(status=status)


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    search_fields = ['name', 'doi', 'dandiset__id', 'version']
    search_help_text = 'Search by name, DOI, Dandiset ID, or version.'
    list_display = [
        'created',
        'modified',
        'dandiset',
        'name',
        'doi',
        'version',
        'status',
        'number_of_assets',
    ]
    list_display_links = ['name']
    list_filter = [VersionStatusFilter]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related('dandiset')

        # Using the `asset_count` property here results in N queries being made
        # for N versions. Instead, use annotation to make one query for N versions.
        return qs.annotate(number_of_assets=Count('assets'))

    def number_of_assets(self, obj):
        return obj.number_of_assets


@admin.register(AssetBlob)
class AssetBlobAdmin(admin.ModelAdmin):
    search_fields = ['blob']
    list_display = ['id', 'blob_id', 'blob', 'references', 'size', 'sha256', 'modified', 'created']
    list_display_links = ['id', 'blob_id']

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('assets')


@admin.register(EmbargoedAssetBlob)
class EmbargoedAssetBlobAdmin(AssetBlobAdmin):
    list_display = [
        'id',
        'blob_id',
        'dandiset',
        'blob',
        'references',
        'size',
        'sha256',
        'modified',
        'created',
    ]


class AssetBlobInline(LimitedTabularInline):
    model = AssetBlob


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    autocomplete_fields = ['blob', 'embargoed_blob', 'zarr', 'versions']
    fields = [
        'asset_id',
        'path',
        'blob',
        'embargoed_blob',
        'zarr',
        'metadata',
        'versions',
        'status',
        'validation_errors',
        'published',
    ]
    list_display = [
        'id',
        'asset_id',
        'path',
        'blob',
        'status',
        'size',
        'modified',
        'created',
    ]
    list_display_links = ['id', 'asset_id', 'path']
    list_select_related = ['zarr', 'blob']


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ['id', 'upload_id', 'blob', 'etag', 'upload_id', 'size', 'created']
    list_display_links = ['id', 'upload_id']
