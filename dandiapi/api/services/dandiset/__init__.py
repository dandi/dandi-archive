from __future__ import annotations

from django.db import transaction

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.version import Version
from dandiapi.api.services.dandiset.exceptions import (
    DandisetAlreadyExistsError,
    DandisetUnEmbargoInProgressError,
)
from dandiapi.api.services.exceptions import AdminOnlyOperationError, NotAllowedError
from dandiapi.api.services.version.metadata import _normalize_version_metadata


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
        dandiset.add_owner(user)
        draft_version = Version(
            dandiset=dandiset,
            name=version_name,
            metadata=version_metadata,
            version='draft',
        )
        draft_version.full_clean(validate_constraints=False)
        draft_version.save()

    return dandiset, draft_version


def delete_dandiset(*, user, dandiset: Dandiset) -> None:
    if not user.has_perm('owner', dandiset):
        raise NotAllowedError('Cannot delete dandisets which you do not own.')
    if dandiset.versions.exclude(version='draft').exists():
        raise NotAllowedError('Cannot delete dandisets with published versions.')
    if dandiset.versions.filter(status=Version.Status.PUBLISHING).exists():
        raise NotAllowedError('Cannot delete dandisets that are currently being published.')
    if dandiset.embargo_status == Dandiset.EmbargoStatus.UNEMBARGOING:
        raise DandisetUnEmbargoInProgressError

    # Delete all versions first, so that AssetPath deletion is cascaded
    # through versions, rather than through zarrs directly
    with transaction.atomic():
        dandiset.versions.all().delete()
        dandiset.delete()
