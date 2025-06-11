from __future__ import annotations

from django.urls import reverse
import pytest


@pytest.mark.django_db
def test_robots_txt(api_client):
    response = api_client.get(reverse('robots_txt'))
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/plain'

    expected_content = """# Allow Googlebot to access dandiset metadata for structured data indexing
User-agent: Googlebot
Allow: /api/dandisets/
Allow: /api/info/
Disallow: /api/dandisets/*/versions/*/assets
Disallow: /

# Disallow all other bots from accessing API endpoints
User-agent: *
Disallow: /
"""

    assert response.content.decode('utf-8').strip() == expected_content.strip()
