from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.version import Version
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
        raise PermissionDenied(
            'Creating a dandiset for a given identifier is an admin only operation.'
        )

    existing_dandiset = Dandiset.objects.filter(id=identifier).first()
    if existing_dandiset:
        raise ValidationError(f'Dandiset {existing_dandiset.identifier} already exists')

    embargo_status = Dandiset.EmbargoStatus.EMBARGOED if embargo else Dandiset.EmbargoStatus.OPEN
    version_metadata = _normalize_version_metadata(
        version_metadata, embargo, f'{user.last_name}, {user.first_name}', user.email
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
    if (
        not user.has_perm('owner', dandiset)
        or dandiset.embargo_status != Dandiset.EmbargoStatus.OPEN
    ):
        raise PermissionDenied()

    if dandiset.versions.exclude(version='draft').exists():
        raise PermissionDenied('Cannot delete dandisets with published versions.')

    dandiset.delete()
