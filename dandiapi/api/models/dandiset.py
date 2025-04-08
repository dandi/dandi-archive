from __future__ import annotations

from django.contrib.auth.models import Group, User
from django.db import models
from django_extensions.db.models import TimeStampedModel
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase


class DandisetPermissions(models.TextChoices):
    # Dandisets
    CREATE_DANDISET = 'create_dandiset', 'Can create the dandiset'
    VIEW_DANDISET = 'view_dandiset', 'Can view the dandiset'
    UPDATE_DANDISET = 'update_dandiset', 'Can update the dandiset'
    DELETE_DANDISET = 'delete_dandiset', 'Can delete the dandiset'
    MANAGE_DANDISET_UPLOADS = 'manage_dandiset_uploads', 'Can manage the dandiset uploads'
    PUBLISH_DANDISET = 'publish_dandiset', 'Can publish the dandiset'
    UNEMBARGO_DANDISET = 'unembargo_dandiset', 'Can unembargo the dandiset'
    STAR_DANDISET = 'star_dandiset', 'Can star the dandiset'
    VIEW_DANDISET_ROLES = 'view_dandiset_roles', 'Can view the dandiset roles'
    UPDATE_DANDISET_ROLES = 'update_dandiset_roles', 'Can update the dandiset roles'

    # Versions
    VIEW_DANDISET_VERSIONS = 'view_dandiset_versions', 'Can view the dandiset versions'

    # Assets
    CREATE_DANDISET_ASSETS = 'create_dandiset_assets', 'Can create the dandiset assets'
    VIEW_DANDISET_ASSETS = 'view_dandiset_assets', 'Can view the dandiset assets'
    DELETE_DANDISET_ASSETS = 'delete_dandiset_assets', 'Can delete the dandiset assets'
    UPDATE_DANDISET_ASSETS = 'update_dandiset_assets', 'Can update the dandiset assets'

    # Zarrs
    VIEW_ZARR_ARCHIVE = 'view_zarr_archive', 'Can view the zarr archive'
    CREATE_ZARR_ARCHIVE = 'create_zarr_archive', 'Can create the zarr archive'
    DELETE_ZARR_ARCHIVE = 'delete_zarr_archive', 'Can delete the zarr archive'
    FINALIZE_ZARR_ARCHIVE = 'finalize_zarr_archive', 'Can finalize the zarr archive'
    CREATE_ZARR_ARCHIVE_FILES = 'create_zarr_archive_files', 'Can create the zarr archive files'
    DELETE_ZARR_ARCHIVE_FILES = 'delete_zarr_archive_files', 'Can delete the zarr archive files'
    LIST_ZARR_ARCHIVE_FILES = 'list_zarr_archive_files', 'Can list the zarr archive files'


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

    class Meta:
        ordering = ['id']
        default_permissions = []
        permissions = [(perm, perm.label) for perm in DandisetPermissions]

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

    def get_owners_group(self):
        return Group.objects.get(dandisetrole__rolename='owners', dandisetrole__dandiset=self)


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
