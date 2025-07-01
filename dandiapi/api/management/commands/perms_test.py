from __future__ import annotations

import typing

from django.contrib.auth.models import Group, Permission, User
from django.db import transaction
import djclick as click
from guardian.shortcuts import assign_perm

from dandiapi.api.models import Dandiset


@click.command()
def perms_test():
    user = typing.cast(
        User, User.objects.filter(is_active=True, is_superuser=False).order_by('?').first()
    )

    dandiset = typing.cast(Dandiset, Dandiset.objects.order_by('?').first())
    owner_user = typing.cast(User, dandiset.get_owners_group().user_set.all().first())

    second_dandiset = typing.cast(Dandiset, Dandiset.objects.order_by('?').first())
    second_owner_user = typing.cast(User, second_dandiset.get_owners_group().user_set.all().first())

    with transaction.atomic():
        # user.user_permissions.clear()
        # owner_user.user_permissions.clear()

        print(user.has_perm('api.view_dandiset', dandiset))
        print(owner_user.has_perm('api.view_dandiset', dandiset))


        # Give user global view perms
        global_view_group = Group.objects.create(name="Global viewer")
        assign_perm(perm='api.view_dandiset', user_or_group=global_view_group)
        user.groups.add(global_view_group)

        # assign_perm('api.view_dandiset', user)
        # assign_perm('api.view_dandiset', owner_user)
        # perm = Permission.objects.get(
        #     codename='view_dandiset', content_type__model=Dandiset._meta.model_name
        # )
        # user.user_permissions.add(perm)
        # owner_user.user_permissions.add(perm)

        # Reset perm cache
        user = User.objects.get(pk=user.pk)
        owner_user = User.objects.get(pk=owner_user.pk)

        print('------------------')
        print(user.has_perm('api.view_dandiset', dandiset))
        print(owner_user.has_perm('api.view_dandiset', dandiset))
        print('------------------')
        print(second_owner_user.has_perm('api.view_dandiset'))
        print(second_owner_user.has_perm('api.view_dandiset', dandiset))
        print(second_owner_user.has_perm('api.view_dandiset', second_dandiset))

        # Abort transaction
        raise Exception('asdads')
