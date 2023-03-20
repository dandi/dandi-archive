from django.contrib import admin, messages
from django.utils.translation import ngettext

from dandiapi.zarr.models import EmbargoedZarrArchive, ZarrArchive
from dandiapi.zarr.tasks import ingest_zarr_archive


@admin.register(ZarrArchive)
class ZarrArchiveAdmin(admin.ModelAdmin):
    search_fields = ['zarr_id', 'name']
    list_display = ['id', 'zarr_id', 'name', 'dandiset']
    list_display_links = ['id', 'zarr_id', 'name']
    actions = ('ingest_zarr_archive',)

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


@admin.register(EmbargoedZarrArchive)
class EmbargoedZarrArchiveAdmin(admin.ModelAdmin):
    search_fields = ['zarr_id', 'name']
    list_display = ['id', 'zarr_id', 'name', 'dandiset']
    list_display_links = ['id', 'zarr_id', 'name']
