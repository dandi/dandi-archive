from __future__ import annotations

import logging
from django.db import transaction

from dandiapi.api import datacite
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

logger = logging.getLogger(__name__)


def create_dandiset(
    *,
    user,
    identifier: int | None = None,
    embargo: bool,
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

    embargo_status = Dandiset.EmbargoStatus.EMBARGOED if embargo else Dandiset.EmbargoStatus.OPEN
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
        
        # For public dandisets, create a Draft DOI
        if not embargo:
            try:
                _create_dandiset_draft_doi(draft_version)
            except Exception as e:
                # Log error but allow dandiset creation to proceed
                logger.exception(f"Failed to create Draft DOI for dandiset {dandiset.identifier}: {e}")
                
    return dandiset, draft_version


def _create_dandiset_draft_doi(draft_version: Version) -> None:
    """
    Create a Draft DOI for a dandiset.
    
    This is called during dandiset creation for public dandisets.
    For embargoed dandisets, no DOI is created until unembargo.
    
    Args:
        draft_version: The draft version of the dandiset.
    """
    if not datacite.doi_configured():
        logger.warning("DOI NOT CONFIGURED. Skipping Draft DOI creation.")
        return
        
    # Generate a Draft DOI (event=None)
    dandiset_doi, dandiset_doi_payload = datacite.generate_doi_data(
        draft_version, 
        version_doi=False, 
        event=None  # Draft DOI
    )
    
    # Create the DOI
    datacite.create_or_update_doi(dandiset_doi_payload)
    
    # Store the DOI in the draft version
    draft_version.doi = dandiset_doi
    draft_version.save()


def delete_dandiset(*, user, dandiset: Dandiset) -> None:
    if not is_dandiset_owner(dandiset, user):
        raise NotAllowedError('Cannot delete dandisets which you do not own.')
    if dandiset.versions.exclude(version='draft').exists():
        raise NotAllowedError('Cannot delete dandisets with published versions.')
    if dandiset.versions.filter(status=Version.Status.PUBLISHING).exists():
        raise NotAllowedError('Cannot delete dandisets that are currently being published.')
    if dandiset.unembargo_in_progress:
        raise DandisetUnembargoInProgressError

    # Check if there's a DOI that needs to be handled
    draft_version = dandiset.versions.filter(version='draft').first()
    has_doi = draft_version and draft_version.doi is not None
    
    # Delete all versions first, so that AssetPath deletion is cascaded
    # through versions, rather than through zarrs directly
    with transaction.atomic():
        # Record the audit event first so that the AuditRecord instance has a
        # chance to grab the Dandiset information before it is destroyed.
        audit.delete_dandiset(dandiset=dandiset, user=user)
        
        # Handle DOI deletion/hiding based on whether it's been published
        if has_doi:
            # If there are published versions, the DOI is Findable and should be hidden
            if dandiset.versions.exclude(version='draft').exists():
                try:
                    datacite.hide_doi(draft_version.doi)
                except Exception as e:
                    logger.exception(f"Failed to hide DOI {draft_version.doi}: {e}")
            # If no published versions, the DOI is a Draft and can be deleted
            else:
                try:
                    datacite.delete_doi(draft_version.doi)
                except Exception as e:
                    logger.exception(f"Failed to delete DOI {draft_version.doi}: {e}")

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