from django.contrib import admin
from django.contrib.admin.options import TabularInline
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.forms.models import BaseInlineFormSet
from guardian.admin import GuardedModelAdmin

from dandiapi.api.models import Asset, AssetBlob, Dandiset, Upload, UserMetadata, Version


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


class AssetInline(LimitedTabularInline):
    model = Asset.versions.through


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ['id', 'dandiset', 'version', 'status', 'asset_count', 'modified', 'created']
    list_display_links = ['id', 'version']
    inlines = [AssetInline]


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
