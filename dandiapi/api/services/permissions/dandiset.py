"""Abstracts over django guardian to provide an internal permission framework."""

from __future__ import annotations

import typing

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import QuerySet
from guardian.shortcuts import assign_perm, get_users_with_perms

from dandiapi.api.models.dandiset import Dandiset, DandisetUserObjectPermission


def add_dandiset_owner(dandiset: Dandiset, user: User):
    pass


@transaction.atomic
def replace_dandiset_owners(dandiset: Dandiset, users: list[User]):
    # Delete all existing owners
    DandisetUserObjectPermission.objects.filter(
        content_object=dandiset.pk, permission__codename='owner'
    ).delete()

    # Set owners to new list
    for user in users:
        assign_perm('owner', user, dandiset)


def get_dandiset_owners(dandiset: Dandiset) -> QuerySet[User]:
    qs = typing.cast(QuerySet[User], get_users_with_perms(dandiset, only_with_perms_in=['owner']))
    return qs.order_by('date_joined')
