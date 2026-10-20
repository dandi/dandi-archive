from __future__ import annotations

from django.conf import settings
from django.db.models import Exists, Max, OuterRef
from django.http import HttpResponse

from dandiapi.api.models import AssetPath, Dandiset


def sitemap_view(request):
    # Only list dandisets that are public and contain data, matching the default dandiset listing
    dandisets = (
        Dandiset.objects.filter(embargo_status=Dandiset.EmbargoStatus.OPEN)
        .filter(Exists(AssetPath.objects.filter(version__dandiset=OuterRef('pk'))))
        .annotate(last_modified=Max('versions__modified'))
        .order_by('id')
    )

    urls = [
        '  <url>\n'
        f'    <loc>{settings.DANDI_WEB_APP_URL}/dandiset/{dandiset.identifier}</loc>\n'
        f'    <lastmod>{dandiset.last_modified.date().isoformat()}</lastmod>\n'
        '  </url>\n'
        for dandiset in dandisets
    ]
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'{"".join(urls)}'
        '</urlset>\n'
    )
    return HttpResponse(content, content_type='application/xml')
