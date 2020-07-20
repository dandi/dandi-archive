from __future__ import annotations

import datetime
import logging

from django.contrib.postgres.fields import JSONField, ArrayField
from django.core.validators import RegexValidator
from django.db import models

from publish.girder import GirderClient
from .common import SelectRelatedManager
from .dandiset import Dandiset

logger = logging.getLogger(__name__)


def _get_default_version() -> str:
    # This cannot be a lambda, as migrations cannot serialize those
    return Version.make_version()


class Contributor(models.Model):
    class RoleType(models.TextChoices):
        Author = "Author"
        Conceptualization = "Conceptualization"
        ContactPerson = "ContactPerson"
        DataCollector = "DataCollector"
        DataCurator = "DataCurator"
        DataManager = "DataManager"
        FormalAnalysis = "FormalAnalysis"
        FundingAcquisition = "FundingAcquisition"
        Investigation = "Investigation"
        Maintainer = "Maintainer"
        Methodology = "Methodology"
        Producer = "Producer"
        ProjectLeader = "ProjectLeader"
        ProjectManager = "ProjectManager"
        ProjectMember = "ProjectMember"
        ProjectAdministration = "ProjectAdministration"
        Researcher = "Researcher"
        Resources = "Resources"
        Software = "Software"
        Supervision = "Supervision"
        Validation = "Validation"
        Visualization = "Visualization"
        Funder = "Funder"
        Sponsor = "Sponsor"
        StudyParticipant = "StudyParticipant"
        Other = "Other"

    name = models.TextField(default=str)
    email = models.TextField(default=str)
    orcid = models.TextField(default=str)
    roles = ArrayField(
        models.CharField(max_length=21, choices=RoleType.choices, default=RoleType.Other),
        default=list
    )
    affiliations = ArrayField(
        models.TextField(default=str), default=list
    )

    def __str__(self) -> str:
        return f'name: {self.name}, email: {self.email}, orcid: {self.orcid}, roles: {self.roles}), affiliations: {self.affiliations}'

    class Meta:
        ordering = ['id']


class Version(models.Model):
    VERSION_REGEX = r'0\.\d{6}\.\d{4}'

    dandiset = models.ForeignKey(Dandiset, related_name='versions', on_delete=models.CASCADE)
    version = models.CharField(
        max_length=13,
        validators=[RegexValidator(f'^{VERSION_REGEX}$')],
        default=_get_default_version,
    )  # TODO: rename this?

    name = models.TextField(default=str)
    description = models.TextField(default=str)

    contributors = models.ManyToManyField(Contributor)

    metadata = JSONField(blank=True, default=dict)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['dandiset', 'version']]
        get_latest_by = 'created'
        ordering = ['dandiset', '-version']
        indexes = [
            models.Index(fields=['dandiset', 'version']),
        ]

    # Define custom "objects" first, so it will be the "_default_manager", which is more efficient
    # for many automatically generated queries
    objects = SelectRelatedManager('dandiset')

    def __str__(self) -> str:
        return f'{self.dandiset.identifier}: {self.version}'

    @property
    def count(self):
        return self.assets.count()

    @property
    def size(self):
        return self.assets.aggregate(total_size=models.Sum('size'))['total_size']

    @staticmethod
    def datetime_to_version(time: datetime.datetime) -> str:
        return time.strftime('0.%y%m%d.%H%M')

    @classmethod
    def make_version(cls, dandiset: Dandiset = None) -> str:
        versions: models.Manager = dandiset.versions if dandiset else cls.objects

        time = datetime.datetime.utcnow()
        # increment time until there are no collisions
        while True:
            version = cls.datetime_to_version(time)
            collision = versions.filter(version=version).exists()
            if not collision:
                break
            time += datetime.timedelta(minutes=1)

        return version

    @classmethod
    def from_girder(cls, dandiset: Dandiset, client: GirderClient) -> Version:
        draft_folder = client.get_json(f'folder/{dandiset.draft_folder_id}')

        metadata = draft_folder['meta']
        name = metadata['dandiset'].pop('name')
        description = metadata['dandiset'].pop('description')
        contributors = metadata['dandiset'].pop('contributors')

        version = Version(dandiset=dandiset,
                          name=name,
                          description=description,
                          metadata=metadata)
        version.save()

        for contributor in contributors:
            new_contributor, succeeded = Contributor.objects.get_or_create(
                name=contributor.get('name'),
                email=contributor.get('email'),
                affiliations=contributor.get('affiliations'),
                orcid=contributor.get('orcid'),
                roles=contributor.get('roles')
            )
            version.contributors.add(new_contributor)

        return version
