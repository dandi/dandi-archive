"""Views for server-rendered dandiset pages."""

from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from dandiapi.api.models import Dandiset, Version
from dandiapi.api.services.embargo.exceptions import UnauthorizedEmbargoAccessError
from dandiapi.api.services.permissions.dandiset import (
    get_dandiset_owners,
    is_dandiset_owner,
)


def dandiset_landing_view(
    request: HttpRequest, identifier: str, version: str = None
) -> HttpResponse:
    """Server-rendered dandiset landing page."""
    try:
        # Convert identifier string to integer ID (identifier is zero-padded ID)
        dandiset_id = int(identifier)
        dandiset = get_object_or_404(Dandiset, id=dandiset_id)

        # Handle version parameter
        if version:
            dandiset_version = get_object_or_404(Version, dandiset=dandiset, version=version)
        else:
            # Default to most recent published version, or draft if no published version
            try:
                dandiset_version = dandiset.most_recent_published_version
                if not dandiset_version:
                    dandiset_version = dandiset.draft_version
            except Exception:
                dandiset_version = dandiset.draft_version

        # Check if user can access this dandiset
        embargoed_or_unauthenticated = False
        user_can_modify_dandiset = False

        try:
            # Check embargo status
            if dandiset.embargo_status == 'EMBARGOED':
                if isinstance(request.user, AnonymousUser) or not is_dandiset_owner(
                    dandiset, request.user
                ):
                    embargoed_or_unauthenticated = True

            # Check if user can modify
            if not isinstance(request.user, AnonymousUser):
                user_can_modify_dandiset = is_dandiset_owner(dandiset, request.user)

        except UnauthorizedEmbargoAccessError:
            embargoed_or_unauthenticated = True

        # Get dandiset stats if available
        stats = None
        if dandiset_version:
            # Try to get stats from metadata or computed fields
            asset_count = getattr(dandiset_version, 'asset_count', 0)
            size = getattr(dandiset_version, 'size', 0)

            # Try to get subject count from metadata
            num_subjects = 0
            if hasattr(dandiset_version, 'metadata') and dandiset_version.metadata:
                metadata = dandiset_version.metadata
                if isinstance(metadata, dict):
                    # Look for assetsSummary in metadata
                    assets_summary = metadata.get('assetsSummary', {})
                    num_subjects = assets_summary.get('numberOfSubjects', 0)

            stats = {
                'num_files': asset_count,
                'size': size,
                'size_display': _format_size_binary(size) if size else '0 B',
                'num_subjects': num_subjects,
            }

        # Get owners
        owners = get_dandiset_owners(dandiset)

        # Find contact person from contributors
        contact_person = None
        if dandiset_version and dandiset_version.metadata:
            metadata = dandiset_version.metadata
            if isinstance(metadata, dict) and 'contributor' in metadata:
                for contributor in metadata['contributor']:
                    if isinstance(contributor, dict) and 'roleName' in contributor:
                        if 'dcite:ContactPerson' in contributor['roleName']:
                            contact_person = contributor.get('name')
                            break

        # Fallback to first owner if no contact person found
        if not contact_person and owners:
            first_owner = owners[0]
            contact_person = first_owner.get_full_name() or first_owner.username

        context = {
            'dandiset': dandiset,
            'dandiset_version': dandiset_version,
            'embargoed_or_unauthenticated': embargoed_or_unauthenticated,
            'dandiset_does_not_exist': False,
            'loading': False,
            'user_can_modify_dandiset': user_can_modify_dandiset,
            'stats': stats,
            'show_pagination': False,  # TODO: Implement pagination
            'current_page': 1,
            'contact_person': contact_person,
        }

        # Add a combined context object that mimics the Vue component structure
        if dandiset_version:
            context['dandiset'] = {
                'dandiset': dandiset,
                'version': dandiset_version.version,
                'metadata': dandiset_version.metadata,
                'owners': owners,
                'star_count': getattr(dandiset, 'star_count', 0),
                'embargo_status': dandiset.embargo_status,
                'doi': getattr(dandiset_version, 'doi', None),
                'contact_person': contact_person,
            }

        return render(request, 'dandiset_landing.html', context)

    except Dandiset.DoesNotExist:
        context = {
            'embargoed_or_unauthenticated': False,
            'dandiset_does_not_exist': True,
            'loading': False,
        }
        return render(request, 'dandiset_landing.html', context)
    except Http404:
        context = {
            'embargoed_or_unauthenticated': False,
            'dandiset_does_not_exist': True,
            'loading': False,
        }
        return render(request, 'dandiset_landing.html', context)


def _format_size(size_bytes: int) -> str:
    """Format size in bytes to human readable format."""
    if size_bytes == 0:
        return '0 B'

    size_names = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f'{size:.1f} {size_names[i]}'


def _format_size_binary(size_bytes: int) -> str:
    """Format size in bytes to binary (MiB, GiB) format like Vue SPA."""
    if size_bytes == 0:
        return '0 B'

    size_names = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    # For sizes less than 1024 bytes, don't show decimal places
    if i == 0:
        return f'{int(size)} {size_names[i]}'
    # Check if decimal part is very small (effectively 0)
    if abs(size - round(size)) < 0.01:  # If difference is less than 0.01
        return f'{int(round(size))} {size_names[i]}'
    return f'{size:.1f} {size_names[i]}'
