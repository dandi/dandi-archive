"""Views for general server-rendered pages."""

from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import OuterRef, Subquery
from django.db.models.query_utils import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from dandiapi.api.models import Version
from dandiapi.api.models.asset_paths import AssetPath
from dandiapi.api.models.stats import ApplicationStats
from dandiapi.api.services.permissions.dandiset import get_visible_dandisets


def home_view(request: HttpRequest) -> HttpResponse:
    """Server-rendered home page."""
    # Fetch latest application statistics
    stats = ApplicationStats.objects.last()

    context = {
        'dandiset_count': stats.dandiset_count if stats else 0,
        'user_count': stats.user_count if stats else 0,
        'total_size_bytes': stats.size if stats else 0,
    }

    return render(request, 'home.html', context)


def dandiset_list_view(request: HttpRequest) -> HttpResponse:
    """Server-rendered dandiset list page."""
    search_query = request.GET.get('search', '')
    page_number = request.GET.get('page', 1)

    # Get base queryset of visible dandisets
    queryset = get_visible_dandisets(request.user).order_by('-created')

    # Filter out empty dandisets
    most_recent_versions = (
        Version.objects.filter(dandiset__in=queryset)
        .order_by('dandiset_id', '-created')
        .distinct('dandiset_id')
    )
    nonempty_version_ids = (
        AssetPath.objects.filter(version__in=most_recent_versions)
        .order_by()
        .distinct('version_id')
        .values_list('version_id', flat=True)
    )
    queryset = queryset.filter(versions__in=nonempty_version_ids)

    # Filter out embargoed dandisets
    queryset = queryset.filter(embargo_status='OPEN')

    # Add search functionality
    if search_query:
        # Search in dandiset identifier, name, and description
        latest_version_subquery = Version.objects.filter(dandiset=OuterRef('pk')).order_by(
            '-created'
        )[:1]

        queryset = queryset.annotate(
            latest_name=Subquery(latest_version_subquery.values('metadata__name')),
            latest_description=Subquery(latest_version_subquery.values('metadata__description')),
        ).filter(
            Q(id__icontains=search_query)
            | Q(latest_name__unaccent__icontains=search_query)
            | Q(latest_description__unaccent__icontains=search_query)
        )

    # Add annotations for template display
    latest_version = Version.objects.filter(dandiset=OuterRef('pk')).order_by('-created')[:1]
    queryset = (
        queryset.annotate(
            version_name=Subquery(latest_version.values('metadata__name')),
            version_description=Subquery(latest_version.values('metadata__description')),
            version_modified=Subquery(latest_version.values('modified')),
        )
        .select_related()
        .order_by('-version_modified')
    )

    # Paginate results
    paginator = Paginator(queryset, 8)  # 8 items per page to match Vue SPA
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'dandiset_list.html',
        {
            'search_query': search_query,
            'dandisets': page_obj,
            'page_obj': page_obj,
        },
    )
