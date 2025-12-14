from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.models import TimeStampedModel
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase


class Dandiset(TimeStampedModel):
    # Don't add beginning and end markers, so this can be embedded in larger regexes
    IDENTIFIER_REGEX = r'\d{6}'

    class EmbargoStatus(models.TextChoices):
        EMBARGOED = 'EMBARGOED', 'Embargoed'
        UNEMBARGOING = 'UNEMBARGOING', 'Unembargoing'
        OPEN = 'OPEN', 'Open'

    embargo_status = models.CharField(
        max_length=max(len(choice[0]) for choice in EmbargoStatus.choices),
        choices=EmbargoStatus.choices,
        default=EmbargoStatus.OPEN,
    )
    starred_users = models.ManyToManyField(
        to=User, through='DandisetStar', related_name='starred_dandisets'
    )
    # Tracks when a publish reminder email was sent to owners of this dandiset.
    # Null means no reminder has been sent yet.
    publish_reminder_sent_at = models.DateTimeField(null=True, blank=True, default=None)

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

    @property
    def star_count(self):
        return self.stars.count()

    def is_starred_by(self, user):
        if not user.is_authenticated:
            return False
        return self.stars.filter(user=user).exists()


class DandisetUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Dandiset, on_delete=models.CASCADE)


class DandisetGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Dandiset, on_delete=models.CASCADE)


class DandisetStar(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dandiset_stars')
    dandiset = models.ForeignKey(Dandiset, on_delete=models.CASCADE, related_name='stars')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(name='unique-user-dandiset-star', fields=['user', 'dandiset'])
        ]

    def __str__(self) -> str:
        return f'Star {self.user.username} ★ {self.dandiset.identifier}'
