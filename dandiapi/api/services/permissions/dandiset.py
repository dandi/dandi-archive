"""Abstracts over django guardian to provide an internal permission framework."""

from __future__ import annotations

import typing

from django.contrib.auth.models import AnonymousUser, User
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils.decorators import method_decorator
from guardian.decorators import permission_required
from guardian.shortcuts import assign_perm, get_objects_for_user, get_users_with_perms

from dandiapi.api.models.dandiset import Dandiset, DandisetUserObjectPermission

if typing.TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

    from dandiapi.api.models.asset import Asset


def get_dandiset_owners(dandiset: Dandiset) -> QuerySet[User]:
    qs = typing.cast(QuerySet[User], get_users_with_perms(dandiset, only_with_perms_in=['owner']))
    return qs.order_by('date_joined')


def add_dandiset_owner(dandiset: Dandiset, user: User):
    assign_perm('owner', user, dandiset)


@transaction.atomic
def replace_dandiset_owners(dandiset: Dandiset, users: list[User]):
    existing_owners = get_dandiset_owners(dandiset)
    existing_owner_set = set(existing_owners)
    new_owner_set = set(users)

    # Delete all existing owners
    DandisetUserObjectPermission.objects.filter(
        content_object=dandiset.pk, permission__codename='owner'
    ).delete()

    # Set owners to new list
    for user in users:
        add_dandiset_owner(dandiset, user)

    # Return the owners added/removed so they can be emailed
    removed_owners = existing_owner_set - new_owner_set
    added_owners = new_owner_set - existing_owner_set
    return removed_owners, added_owners


def is_dandiset_owner(dandiset: Dandiset, user: AbstractBaseUser | AnonymousUser) -> bool:
    if isinstance(user, AnonymousUser):
        return False

    user = typing.cast(User, user)
    return user.has_perm('owner', dandiset)


def is_owned_asset(asset: Asset, user: AbstractBaseUser | AnonymousUser) -> bool:
    """Return `True` if this asset belongs to a dandiset that the user is an owner of."""
    if user.is_anonymous:
        return False

    user = typing.cast(User, user)
    asset_dandisets = Dandiset.objects.filter(versions__in=asset.versions.all())
    asset_dandisets_owned_by_user = DandisetUserObjectPermission.objects.filter(
        content_object__in=asset_dandisets,
        user=user,
        permission__codename='owner',
    )

    return asset_dandisets_owned_by_user.exists()


def get_owned_dandisets(
    user: AbstractBaseUser | AnonymousUser,
    include_superusers=True,  # noqa: FBT002
) -> QuerySet[Dandiset]:
    return get_objects_for_user(user, 'owner', Dandiset, with_superuser=include_superusers)


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


def require_dandiset_owner_or_403(pk_path: str):
    """
    Decorate viewset methods to only allow access to dandiset owners.

    The `pk_path` argument is the Dandiset ID URL path variable that DRF passes into the request.
    """
    return method_decorator(
        permission_required(
            perm='owner', lookup_variables=(Dandiset, 'pk', pk_path), return_403=True
        )
    )
