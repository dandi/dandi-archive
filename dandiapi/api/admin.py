from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from dandiapi.api.models import (
    Asset,
    AssetBlob,
    AssetMetadata,
    Dandiset,
    Upload,
    Version,
    VersionMetadata,
)


@admin.register(Dandiset)
class DandisetAdmin(GuardedModelAdmin):
    list_display = ['identifier', 'modified', 'created']
    readonly_fields = ['identifier', 'created']


@admin.register(VersionMetadata)
class VersionMetadataAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'metadata', 'references', 'modified', 'created']
    list_display_links = ['id', 'name', 'metadata']


class AssetInline(admin.TabularInline):
    model = Asset.versions.through


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ['id', 'dandiset', 'version', 'asset_count', 'modified', 'created']
    list_display_links = ['id', 'version']
    inlines = [AssetInline]


@admin.register(AssetBlob)
class AssetBlobAdmin(admin.ModelAdmin):
    list_display = ['id', 'blob_id', 'blob', 'references', 'size', 'sha256', 'modified', 'created']
    list_display_links = ['id', 'blob_id']


@admin.register(AssetMetadata)
class AssetMetadataAdmin(admin.ModelAdmin):
    list_display = ['id', 'metadata', 'references', 'modified', 'created']
    list_display_links = ['id', 'metadata']


class AssetBlobInline(admin.TabularInline):
    model = AssetBlob


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    # list_display = ['id', 'uuid', 'path']
    # list_display_links = ['id', 'uuid']
    list_display = [
        'id',
        'uuid',
        'path',
        'blob',
        'metadata',
        'size',
        'modified',
        'created',
    ]
    list_display_links = ['id', 'uuid', 'path']
    # inlines = [AssetBlobInline]


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ['id', 'upload_id', 'blob', 'etag', 'upload_id', 'size', 'modified', 'created']
    list_display_links = ['id', 'upload_id']
