from __future__ import annotations

from django.http import HttpResponse


def robots_txt_view(request):
    content = """# Allow Googlebot to access dandiset metadata for structured data indexing
User-agent: Googlebot
Allow: /api/dandisets/*/versions/*/info
Allow: /api/dandisets/*/versions/*/
Allow: /api/dandisets/*/info
Allow: /api/dandisets/*/
Allow: /api/info/
Disallow: /api/

# Disallow all other bots from accessing API endpoints
User-agent: *
Disallow: /api/
Disallow: /admin/
Disallow: /oauth/
Disallow: /swagger/
"""
    return HttpResponse(content, content_type='text/plain')
