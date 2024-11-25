from django.views.decorators.cache import cache_page
from django.http import HttpResponse

@cache_page(60 * 60 * 24)  # 24 hour cache
def robots_txt_view(request):
    content = """
    User-agent: *
    Disallow: /
    """
    return HttpResponse(content, content_type="text/plain")
