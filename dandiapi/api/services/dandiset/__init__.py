from __future__ import annotations

from django.db import transaction

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.version import Version
from dandiapi.api.services import audit
from dandiapi.api.services.dandiset.exceptions import DandisetAlreadyExistsError
from dandiapi.api.services.embargo.exceptions import DandisetUnembargoInProgressError
from dandiapi.api.services.exceptions import AdminOnlyOperationError, NotAllowedError
from dandiapi.api.services.permissions.dandiset import add_dandiset_owner, is_dandiset_owner
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
