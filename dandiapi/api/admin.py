from django.contrib import admin
from django.contrib.admin.options import TabularInline
from django.contrib.auth.admin import UserAdmin
from django.db.models.aggregates import Count
from django.db.models.query import QuerySet
from django.forms.models import BaseInlineFormSet
from django.http.request import HttpRequest
from guardian.admin import GuardedModelAdmin

from dandiapi.api.models import (
    Asset,
    AssetBlob,
    Dandiset,
    Upload,
    UserMetadata,
    Version,
    ZarrArchive,
    ZarrUploadFile,
)


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


class UserMetadataInline(TabularInline):
    model = UserMetadata
    fields = ['status', 'questionnaire_form', 'rejection_reason']


UserAdmin.inlines = [UserMetadataInline]


@admin.register(ZarrArchive)
class ZarrArchiveAdmin(admin.ModelAdmin):
    list_display = ['id', 'zarr_id', 'name']
    list_display_links = ['id', 'zarr_id', 'name']


@admin.register(ZarrUploadFile)
class ZarrUploadFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'zarr_archive', 'path', 'blob', 'etag']
    list_display_links = ['id']
