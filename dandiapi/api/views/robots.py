from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse


def robots_txt_view(request):
    content = f"""# Allow Googlebot to access dandiset metadata for structured data indexing
User-agent: Googlebot
Allow: /api/dandisets/search
Allow: /api/dandisets/*/
Allow: /api/dandisets/?
Allow: /api/info/
Allow: /api/dandisets/*/versions/*/assets*page_size=1
Disallow: /api/dandisets/*/versions/*/assets
Disallow: /

# Disallow all other bots from accessing API endpoints
User-agent: *
Disallow: /

# Sitemap location
Sitemap: {settings.DANDI_API_URL}/sitemap.xml
"""
    return HttpResponse(content, content_type='text/plain')
