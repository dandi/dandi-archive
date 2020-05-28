from django.contrib import admin

from .models import Asset, Dandiset, Version


@admin.register(Dandiset)
class DandisetAdmin(admin.ModelAdmin):
    readonly_fields = ['identifier']


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ['id', 'dandiset', 'version']
    list_display_links = ['id', 'version']


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['id', 'uuid', 'path']
    list_display_links = ['id', 'uuid']
