from __future__ import annotations

from django.contrib import admin, messages
from django.utils.translation import ngettext

from dandiapi.zarr.models import ZarrArchive
from dandiapi.zarr.tasks import ingest_zarr_archive


@admin.register(ZarrArchive)
class ZarrArchiveAdmin(admin.ModelAdmin):
    search_fields = ['zarr_id', 'name']
    list_display = ['id', 'zarr_id', 'name', 'dandiset', 'public']
    list_display_links = ['id', 'zarr_id', 'name']
    actions = ('ingest_zarr_archive',)

    @admin.display(boolean=True, description='Public Access', ordering='embargoed')
    def public(self, obj: ZarrArchive):
        return not obj.embargoed

    @admin.action(description='Ingest selected zarr archives')
    def ingest_zarr_archive(self, request, queryset):
        for zarr in queryset:
            ingest_zarr_archive.delay(zarr_id=(str(zarr.zarr_id)), force=True)

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
