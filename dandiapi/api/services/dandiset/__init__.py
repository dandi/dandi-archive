from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from django.contrib.auth.models import User

from dandischema.models import AccessRequirements, AccessType, Organization, RoleType

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


def _create_dandiset(
    *,
    user: User,
    identifier: int | None = None,
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

    version_metadata = _normalize_version_metadata(
        version_metadata, f'{user.last_name}, {user.first_name}', user.email
    )

    with transaction.atomic():
        dandiset = Dandiset(id=identifier)
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

    return dandiset, draft_version


def create_open_dandiset(
    *,
    user: User,
    identifier: int | None = None,
    version_name: str,
    version_metadata: dict,
) -> tuple[Dandiset, Version]:
    with transaction.atomic():
        dandiset, draft_version = _create_dandiset(
            user=user,
            identifier=identifier,
            version_name=version_name,
            version_metadata=version_metadata,
        )

        audit.create_dandiset(dandiset=dandiset, user=user, metadata=draft_version.metadata)

    return dandiset, draft_version


def create_embargoed_dandiset(  # noqa: PLR0913
    *,
    user: User,
    identifier: int | None = None,
    version_name: str,
    version_metadata: dict,
    funding_source: str | None,
    award_number: str | None,
    embargo_end_date: datetime,
):
    with transaction.atomic():
        dandiset, draft_version = _create_dandiset(
            user=user,
            identifier=identifier,
            version_name=version_name,
            version_metadata=version_metadata,
        )

        dandiset.embargo_status = Dandiset.EmbargoStatus.EMBARGOED

        version_metadata['access'] = [
            AccessRequirements(
                schemaKey='AccessRequirements',
                status=AccessType.EmbargoedAccess,
                embargoedUntil=embargo_end_date,
            ).json_dict()
        ]

        if funding_source:
            contributors = version_metadata.get('contributor')
            if contributors is None or not isinstance(contributors, list):
                contributors = []

            kwargs = {
                'name': funding_source,
                'schemaKey': 'Organization',
                'roleName': RoleType.Funder.value,
            }
            if award_number:
                kwargs['award_number'] = award_number

            contributors.append(Organization(**kwargs).json_dict())
            draft_version.metadata['contributor'] = contributors

        dandiset.full_clean()
        dandiset.save()

        draft_version.full_clean(validate_constraints=False)
        draft_version.save()

        audit.create_dandiset(dandiset=dandiset, user=user, metadata=draft_version.metadata)

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
