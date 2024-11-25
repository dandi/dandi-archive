from __future__ import annotations

from django.http import HttpResponse


def robots_txt_view(request):
    content = 'User-agent: *\nDisallow: /'
    return HttpResponse(content, content_type='text/plain')
