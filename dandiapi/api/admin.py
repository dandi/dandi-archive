import csv

from django.contrib import admin, messages
from django.contrib.admin.options import TabularInline
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models.aggregates import Count
from django.db.models.query import QuerySet
from django.forms.models import BaseInlineFormSet
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ngettext
from guardian.admin import GuardedModelAdmin

from dandiapi.api.models import (
    Asset,
    AssetBlob,
    Dandiset,
    EmbargoedZarrArchive,
    EmbargoedZarrUploadFile,
    Upload,
    UserMetadata,
    Version,
    ZarrArchive,
    ZarrUploadFile,
)
from dandiapi.api.tasks.zarr import ingest_dandiset_zarrs, ingest_zarr_archive
from dandiapi.api.views.users import social_account_to_dict

admin.site.site_header = 'DANDI Admin'
admin.site.site_title = 'DANDI Admin'


class UserMetadataInline(TabularInline):
    model = UserMetadata
    fields = ['status', 'questionnaire_form', 'rejection_reason']


class UserAdmin(BaseUserAdmin):
    list_select_related = ['metadata']
    list_display = ['email', 'first_name', 'last_name', 'github_username', 'status', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    inlines = [UserMetadataInline]

    @admin.action(description="Export selected users\' emails")
    def export_emails_to_plaintext(self, request, queryset):
        response = HttpResponse(content_type='text/plain')
        writer = csv.writer(response)
        emails = [obj.email for obj in queryset]
        writer.writerow(emails)
        return response

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.list_filter = ('metadata__status',) + self.list_filter
        self.actions += ['export_emails_to_csv', 'export_emails_to_plaintext']

    @admin.display()
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
    inlines = [VersionInline]

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
        self.actions += ['ingest_dandiset_zarrs']


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'dandiset',
        'version',
        'status',
        'number_of_assets',
        'modified',
        'created',
    ]
    list_display_links = ['id', 'version']

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        # Using the `asset_count` property here results in N queries being made
        # for N versions. Instead, use annotation to make one query for N versions.
        return super().get_queryset(request).annotate(number_of_assets=Count('assets'))

    def number_of_assets(self, obj):
        return obj.number_of_assets


@admin.register(AssetBlob)
class AssetBlobAdmin(admin.ModelAdmin):
    list_display = ['id', 'blob_id', 'blob', 'references', 'size', 'sha256', 'modified', 'created']
    list_display_links = ['id', 'blob_id']


class AssetBlobInline(LimitedTabularInline):
    model = AssetBlob


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    # list_display = ['id', 'uuid', 'path']
    # list_display_links = ['id', 'uuid']
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
    # inlines = [AssetBlobInline]


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ['id', 'upload_id', 'blob', 'etag', 'upload_id', 'size', 'modified', 'created']
    list_display_links = ['id', 'upload_id']


@admin.register(ZarrArchive)
class ZarrArchiveAdmin(admin.ModelAdmin):
    list_display = ['id', 'zarr_id', 'name', 'dandiset']
    list_display_links = ['id', 'zarr_id', 'name']

    @admin.action(description='Ingest selected zarr archives')
    def ingest_zarr_archive(self, request, queryset):
        for zarr in queryset:
            ingest_zarr_archive.delay(zarr_id=(str(zarr.zarr_id)))

        # Return message
        self.message_user(
            request,
            ngettext(
                '%d zarr archive has begun ingesting.',
                '%d zarr archives have begun ingesting.',
                queryset.count(),
            )
            % queryset.count(),
            messages.SUCCESS,
        )

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.actions += ['ingest_zarr_archive']


@admin.register(EmbargoedZarrArchive)
class EmbargoedZarrArchiveAdmin(admin.ModelAdmin):
    list_display = ['id', 'zarr_id', 'name', 'dandiset']
    list_display_links = ['id', 'zarr_id', 'name']


@admin.register(ZarrUploadFile)
class ZarrUploadFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'zarr_archive', 'path', 'blob', 'etag']
    list_display_links = ['id']


@admin.register(EmbargoedZarrUploadFile)
class EmbargoedZarrUploadFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'zarr_archive', 'path', 'blob', 'etag']
    list_display_links = ['id']
