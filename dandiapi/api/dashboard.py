from django.core.exceptions import PermissionDenied
from django.db.models import Exists, OuterRef, Q
from django.views.generic.base import TemplateView

from dandiapi.api.models import Asset, AssetBlob, Version


class DashboardView(TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        if not self.request.user.is_superuser:
            raise PermissionDenied()
        context = super().get_context_data(**kwargs)
        context['orphaned_asset_count'] = self._orphaned_asset_count()
        context['orphaned_asset_blob_count'] = self._orphaned_asset_blob_count()
        non_valid_assets = self._non_valid_assets()
        context['non_valid_asset_count'] = non_valid_assets.count()
        context['non_valid_assets'] = non_valid_assets[:10]

        return context

    def _orphaned_asset_count(self):
        return (
            Asset.objects.annotate(
                has_version=Exists(Version.objects.filter(assets=OuterRef('id')))
            )
            .filter(has_version=False)
            .count()
        )

    def _orphaned_asset_blob_count(self):
        return (
            AssetBlob.objects.annotate(
                has_asset=Exists(Asset.objects.filter(blob_id=OuterRef('id')))
            )
            .filter(has_asset=False)
            .count()
        )

    def _non_valid_assets(self):
        return (
            Asset.objects.annotate(
                has_version=Exists(Version.objects.filter(assets=OuterRef('id')))
            )
            .filter(has_version=True)
            .filter(~Q(status=Asset.Status.VALID))
        )
