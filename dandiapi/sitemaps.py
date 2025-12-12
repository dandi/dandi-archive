from __future__ import annotations

from django.contrib.sitemaps import Sitemap

from dandiapi.api.models.dandiset import Dandiset


class DandisetSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.5

    def items(self):
        return Dandiset.objects.filter(embargo_status=Dandiset.EmbargoStatus.OPEN)

    def location(self, obj: Dandiset) -> str:
        return f'/dandiset/{obj.identifier}/'

    def get_domain(self, site):
        return 'dandiarchive.org'


sitemaps = {
    'dandisets': DandisetSitemap,
}
