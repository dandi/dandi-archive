from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from dandiapi.api.models import Asset, AssetBlob, AssetMetadata, Dandiset, Version, VersionMetadata


@admin.register(Dandiset)
class DandisetAdmin(GuardedModelAdmin):
    list_display = ['identifier', 'modified', 'created']
    readonly_fields = ['identifier', 'created']


@admin.register(VersionMetadata)
class VersionMetadataAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'metadata', 'references', 'modified', 'created']
    list_display_links = ['id', 'name', 'metadata']


class AssetInline(admin.TabularInline):
    model = Asset


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ['id', 'dandiset', 'version', 'asset_count', 'modified', 'created']
    list_display_links = ['id', 'version']
    inlines = [AssetInline]


@admin.register(AssetBlob)
class AssetBlobAdmin(admin.ModelAdmin):
    list_display = ['id', 'path', 'blob', 'references', 'modified', 'created']
    list_display_links = ['id', 'path', 'blob']


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
    list_display = ['id', 'path', 'version', 'blob', 'metadata', 'modified', 'created']
    list_display_links = ['id', 'path']
    # inlines = [AssetBlobInline]
