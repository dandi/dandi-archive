from django.contrib import admin

from dandi.publish.models import Asset, Dandiset, DraftVersion, Version


@admin.register(Dandiset)
class DandisetAdmin(admin.ModelAdmin):
    readonly_fields = ['identifier']


@admin.register(DraftVersion)
class DraftVersionAdmin(admin.ModelAdmin):
    list_display = ['dandiset', 'name']
    list_display_links = ['dandiset', 'name']


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ['id', 'dandiset', 'version']
    list_display_links = ['id', 'version']


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['id', 'uuid', 'path']
    list_display_links = ['id', 'uuid']
