from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sitemaps import Sitemap

from dandiapi.api.models.dandiset import Dandiset


class DandisetSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.5

    def items(self):
        if settings.DANDI_ENABLE_SITEMAP_XML:
            return Dandiset.objects.filter(embargo_status=Dandiset.EmbargoStatus.OPEN)
        return Dandiset.objects.none()

    def location(self, obj: Dandiset) -> str:
        return f'/dandiset/{obj.identifier}/'

    def get_domain(self, site):
        return urlparse(settings.DANDI_WEB_APP_URL).netloc


sitemaps = {
    'dandisets': DandisetSitemap,
}
