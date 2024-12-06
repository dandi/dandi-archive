from __future__ import annotations

import typing

from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.models import TimeStampedModel
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import get_objects_for_user

from dandiapi.api.services.permissions.dandiset import get_dandiset_owners, replace_dandiset_owners


class DandisetManager(models.Manager):
    def visible_to(self, user) -> models.QuerySet[Dandiset]:
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
        owned_dandiset_pks = get_objects_for_user(user, 'owner', Dandiset).values('pk').all()
        return self.filter(
            models.Q(embargo_status=Dandiset.EmbargoStatus.OPEN)
            | models.Q(pk__in=owned_dandiset_pks)
        ).order_by('created')


class Dandiset(TimeStampedModel):
    # Don't add beginning and end markers, so this can be embedded in larger regexes
    IDENTIFIER_REGEX = r'\d{6}'

    objects: DandisetManager = DandisetManager()

    class EmbargoStatus(models.TextChoices):
        EMBARGOED = 'EMBARGOED', 'Embargoed'
        UNEMBARGOING = 'UNEMBARGOING', 'Unembargoing'
        OPEN = 'OPEN', 'Open'

    embargo_status = models.CharField(
        max_length=max(len(choice[0]) for choice in EmbargoStatus.choices),
        choices=EmbargoStatus.choices,
        default=EmbargoStatus.OPEN,
    )

    class Meta:
        ordering = ['id']
        permissions = [('owner', 'Owns the dandiset')]

    @property
    def identifier(self) -> str:
        # Compare against None, to allow id 0
        return f'{self.id:06}' if self.id is not None else ''

    @property
    def embargoed(self) -> bool:
        return self.embargo_status == self.EmbargoStatus.EMBARGOED

    @property
    def unembargo_in_progress(self) -> bool:
        return self.embargo_status == self.EmbargoStatus.UNEMBARGOING

    @property
    def most_recent_published_version(self):
        return self.versions.exclude(version='draft').order_by('modified').last()

    @property
    def draft_version(self):
        return self.versions.filter(version='draft').get()

    @property
    def owners(self):
        return get_dandiset_owners(self)

    def set_owners(self, new_owners: list[User]):
        old_owners = get_dandiset_owners(self)
        replace_dandiset_owners(self, new_owners)

        # Removed owners are users that are in old_owners, but not in new_owners
        # Added owers are users that are in new_owners, but not old_owners
        old_owner_set = typing.cast(set[User], set(old_owners))
        new_owner_set = set(new_owners)
        removed_owners = old_owner_set - new_owner_set
        added_owners = new_owner_set - old_owner_set

        # Return the owners added/removed so they can be emailed
        return removed_owners, added_owners

    @classmethod
    def published_count(cls):
        """Return the number of Dandisets with published Versions."""
        # Prevent circular import
        from .version import Version

        # It's not possible to efficiently filter by a reverse relation (.versions),
        # so this is an efficient alternative
        return Version.objects.exclude(version='draft').values('dandiset').distinct().count()

    def __str__(self) -> str:
        return self.identifier


class DandisetUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Dandiset, on_delete=models.CASCADE)


class DandisetGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Dandiset, on_delete=models.CASCADE)
