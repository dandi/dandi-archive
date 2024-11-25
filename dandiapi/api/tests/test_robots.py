import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_robots_txt(api_client):
    response = api_client.get(reverse('robots_txt'))
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/plain'
    expected_content = """
    User-agent: *
    Disallow: /
    """
    assert response.content.decode('utf-8').strip() == expected_content.strip()
