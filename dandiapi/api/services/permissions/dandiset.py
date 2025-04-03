"""Abstracts over django guardian to provide an internal permission framework."""

from __future__ import annotations

import typing

from django.contrib.auth.models import AnonymousUser, User
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils.decorators import method_decorator
from guardian.decorators import permission_required
from guardian.shortcuts import get_objects_for_user

from dandiapi.api.models.dandiset import (
    Dandiset,
    DandisetGroupObjectPermission,
    DandisetPermissions,
)

if typing.TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

    from dandiapi.api.models.asset import Asset


def get_dandiset_owners(dandiset: Dandiset) -> QuerySet[User]:
    return User.objects.filter(groups=dandiset.get_owners_group()).order_by('date_joined')


def add_dandiset_owner(dandiset: Dandiset, user: User):
    user.groups.add(dandiset.get_owners_group())


def replace_dandiset_owners(dandiset: Dandiset, users: list[User]):
    existing_owners = get_dandiset_owners(dandiset)
    existing_owner_set = set(existing_owners)
    new_owner_set = set(users)

    with transaction.atomic():
        # Delete all existing owners
        dandiset.get_owners_group().user_set.clear()

        # Set owners to new list
        for user in users:
            add_dandiset_owner(dandiset, user)

    # Return the owners added/removed so they can be emailed
    removed_owners = existing_owner_set - new_owner_set
    added_owners = new_owner_set - existing_owner_set
    return removed_owners, added_owners


def has_dandiset_perm(
    dandiset: Dandiset, user: AbstractBaseUser | AnonymousUser, perm: DandisetPermissions
) -> bool:
    """Return `True` if `user` has `perm` on `dandiset`."""
    if user.is_anonymous:
        return False

    user = typing.cast('User', user)
    return user.has_perm(perm=perm, obj=dandiset)


def has_asset_perm(
    asset: Asset, user: AbstractBaseUser | AnonymousUser, perm: DandisetPermissions
) -> bool:
    """Return `True` if this asset belongs to a dandiset that the user has the given permission."""
    if user.is_anonymous:
        return False

    user = typing.cast('User', user)
    asset_dandisets = Dandiset.objects.filter(versions__in=asset.versions.all())
    dandisets_with_perm = get_objects_for_user(user=user, perms=perm, klass=asset_dandisets)
    return dandisets_with_perm.exists()


def get_owned_dandisets(
    user: AbstractBaseUser | AnonymousUser, *, include_superusers=True
) -> QuerySet[Dandiset]:
    user = typing.cast('User', user)

    # Superusers have the same permissions as dandiset owners, but on all dandisets
    if include_superusers and user.is_superuser:
        return Dandiset.objects.all()
    if user.is_anonymous:
        return Dandiset.objects.none()

    # Group name is the sole criteria for distinguishing groups
    regex = r'Dandiset (\d{6}) Owners'

    # This is a slightly roundabout way of getting the dandisets that this user is an owner of.
    # Until we have a direct relation between groups and dandisets, this will have to do.
    dandiset_ids = (
        DandisetGroupObjectPermission.objects.all()
        .filter(group__user=user, group__name__regex=regex)
        .values_list('content_object', flat=True)
        .distinct()
    )

    return Dandiset.objects.filter(id__in=dandiset_ids)


def get_visible_dandisets(user: AbstractBaseUser | AnonymousUser) -> QuerySet[Dandiset]:
    """
    Return a queryset containing all dandisets visible to the given user.

    This is basically all dandisets except embargoed dandisets not owned by the given user.
    """
    # We would like to do something like:
    # Dandiset.filter(embargo_status=OPEN | permission__owned)
    # but this is not possible with django-guardian; the `get_objects_for_user` shortcut must
    # be used instead.
    # We would like to do something like:
    # queryset = Dandiset.objects.filter(embargo_status=OPEN).union(get_objects_for_user(...))
    # but you cannot filter or perform many other common queryset operations after using
    # union().
    # Therefore, we resort to fetching the list of all primary keys for dandisets owned by the
    # current user with `get_objects_for_user(...)`, then filter for either those dandisets or
    # OPEN dandisets. There aren't very many dandisets and most users won't own very many of
    # them, so there shouldn't be too many dandisets in the list.

    owned_dandiset_pks = get_owned_dandisets(user).values('pk').all()
    return Dandiset.objects.filter(
        Q(embargo_status=Dandiset.EmbargoStatus.OPEN) | Q(pk__in=owned_dandiset_pks)
    ).order_by('created')


def require_dandiset_perm_or_403(pk_path: str, *, perm: DandisetPermissions):
    """
    Decorate viewset methods to only allow access to dandiset owners.

    The `pk_path` argument is the Dandiset ID URL path variable that DRF passes into the request.
    """
    return method_decorator(
        permission_required(perm=perm, lookup_variables=(Dandiset, 'pk', pk_path), return_403=True)
    )
