from __future__ import annotations

from django.db import transaction

from dandiapi.api.models.dandiset import Dandiset, DandisetStar
from dandiapi.api.models.version import Version
from dandiapi.api.services import audit
from dandiapi.api.services.dandiset.exceptions import DandisetAlreadyExistsError
from dandiapi.api.services.embargo.exceptions import DandisetUnembargoInProgressError
from dandiapi.api.services.exceptions import (
    AdminOnlyOperationError,
    NotAllowedError,
    NotAuthenticatedError,
)
from dandiapi.api.services.permissions.dandiset import add_dandiset_owner, is_dandiset_owner
from dandiapi.api.services.version.metadata import _normalize_version_metadata


def create_dandiset(
    *,
    user,
    identifier: int | None = None,
    embargo_config: dict,
    version_name: str,
    version_metadata: dict,
) -> tuple[Dandiset, Version]:
    if identifier and not user.is_superuser:
        raise AdminOnlyOperationError(
            'Creating a dandiset for a given identifier is an admin only operation.'
        )

    existing_dandiset = Dandiset.objects.filter(id=identifier).first()
    if existing_dandiset:
        raise DandisetAlreadyExistsError(f'Dandiset {existing_dandiset.identifier} already exists')

    embargo = embargo_config.get('embargo', False)
    embargo_status = Dandiset.EmbargoStatus.EMBARGOED if embargo else Dandiset.EmbargoStatus.OPEN

    # Handle embargo parameters - add funding info to contributors and set embargo end date
    if embargo:
        funding_source = embargo_config.get('funding_source')
        award_number = embargo_config.get('award_number')
        grant_end_date = embargo_config.get('grant_end_date')
        embargo_end_date = embargo_config.get('embargo_end_date')

        # Determine the embargo end date
        if grant_end_date:
            # Use grant end date for award-based embargoes
            embargo_until = grant_end_date
        elif embargo_end_date:
            # Use explicit embargo end date
            embargo_until = embargo_end_date
        else:
            # Default to 2 years from now if no date specified
            from datetime import datetime, timedelta, timezone

            embargo_until = (datetime.now(tz=timezone.UTC) + timedelta(days=730)).strftime(
                '%Y-%m-%d'
            )

        # Set access metadata with embargo end date
        version_metadata['access'] = [
            {
                'schemaKey': 'AccessRequirements',
                'status': 'dandi:EmbargoedAccess',
                'embargoedUntil': embargo_until,
            }
        ]

        if funding_source:
            # Add funding organization as a contributor
            funding_org = {
                'name': funding_source,
                'schemaKey': 'Organization',
                'roleName': ['dcite:Funder'],
            }

            if award_number:
                funding_org['awardNumber'] = award_number

            # Add to contributors if not already present
            contributors = version_metadata.get('contributor', [])
            contributors.append(funding_org)
            version_metadata['contributor'] = contributors

    version_metadata = _normalize_version_metadata(
        version_metadata, f'{user.last_name}, {user.first_name}', user.email, embargo=embargo
    )

    with transaction.atomic():
        dandiset = Dandiset(id=identifier, embargo_status=embargo_status)
        dandiset.full_clean()
        dandiset.save()
        add_dandiset_owner(dandiset, user)
        draft_version = Version(
            dandiset=dandiset,
            name=version_name,
            metadata=version_metadata,
            version='draft',
        )
        draft_version.full_clean(validate_constraints=False)
        draft_version.save()

        audit.create_dandiset(
            dandiset=dandiset, user=user, metadata=draft_version.metadata, embargoed=embargo
        )

    return dandiset, draft_version


def delete_dandiset(*, user, dandiset: Dandiset) -> None:
    if not is_dandiset_owner(dandiset, user):
        raise NotAllowedError('Cannot delete dandisets which you do not own.')
    if dandiset.versions.exclude(version='draft').exists():
        raise NotAllowedError('Cannot delete dandisets with published versions.')
    if dandiset.versions.filter(status=Version.Status.PUBLISHING).exists():
        raise NotAllowedError('Cannot delete dandisets that are currently being published.')
    if dandiset.unembargo_in_progress:
        raise DandisetUnembargoInProgressError

    # Delete all versions first, so that AssetPath deletion is cascaded
    # through versions, rather than through zarrs directly
    with transaction.atomic():
        # Record the audit event first so that the AuditRecord instance has a
        # chance to grab the Dandiset information before it is destroyed.
        audit.delete_dandiset(dandiset=dandiset, user=user)

        dandiset.versions.all().delete()
        dandiset.delete()


def star_dandiset(*, user, dandiset: Dandiset) -> int:
    """
    Star a Dandiset for a user.

    Args:
        user: The user starring the Dandiset.
        dandiset: The Dandiset to star.

    Returns:
        The new star count for the Dandiset.
    """
    if not user.is_authenticated:
        raise NotAuthenticatedError

    DandisetStar.objects.get_or_create(user=user, dandiset=dandiset)
    return dandiset.star_count


def unstar_dandiset(*, user, dandiset: Dandiset) -> int:
    """
    Unstar a Dandiset for a user.

    Args:
        user: The user unstarring the Dandiset.
        dandiset: The Dandiset to unstar.

    Returns:
        The new star count for the Dandiset.
    """
    if not user.is_authenticated:
        raise NotAuthenticatedError

    DandisetStar.objects.filter(user=user, dandiset=dandiset).delete()
    return dandiset.star_count
