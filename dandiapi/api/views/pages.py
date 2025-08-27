"""Views for general server-rendered pages."""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home_view(request: HttpRequest) -> HttpResponse:
    """Server-rendered home page."""
    return render(request, 'home.html')