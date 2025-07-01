from __future__ import annotations

import datetime
import hashlib

from allauth.socialaccount.models import SocialAccount
from dandischema.digests.dandietag import DandiETag
from dandischema.models import AccessType
from django.conf import settings
from django.contrib.auth.models import User
from django.core import files as django_files
import factory
import faker

from dandiapi.api.models import (
    Asset,
    AssetBlob,
    Dandiset,
    Upload,
    UserMetadata,
    Version,
)
from dandiapi.api.models.dandiset import DandisetPermissions
from dandiapi.api.services.dandiset import _create_dandiset_role
from dandiapi.api.services.publish import publish_asset


class UserMetadataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserMetadata

    status = UserMetadata.Status.APPROVED.value


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.SelfAttribute('email')
    email = factory.Faker('free_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

    metadata = factory.RelatedFactory(UserMetadataFactory, factory_related_name='user')


class SocialAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SocialAccount

    user = factory.SubFactory(UserFactory)
    uid = factory.Faker('sha1')

    @factory.lazy_attribute
    def extra_data(self):
        first_name = self.user.first_name
        last_name = self.user.last_name
        name = f'{first_name} {last_name}'

        # Supply a fake created date at least 1 year before now
        created = (
            faker.Faker()
            .date_time_between(
                end_date=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=365)
            )
            .isoformat()
        )

        # Supply different values from User object, since social account values maybe be different
        return {
            'login': faker.Faker().user_name(),
            'name': name,
            'email': faker.Faker().ascii_email(),
            'created_at': created,
        }


class DandisetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Dandiset

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        dandiset = manager.create(*args, **kwargs)
        _create_dandiset_role(dandiset=dandiset, rolename='owner', perms=list(DandisetPermissions))
        return dandiset


class BaseVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    dandiset = factory.SubFactory(DandisetFactory)
    name = factory.Faker('sentence')

    @factory.lazy_attribute
    def version(self):
        return Version.next_published_version(self.dandiset)

    @factory.lazy_attribute
    def metadata(self):
        metadata = {
            **faker.Faker().pydict(value_types=['str', 'float', 'int']),
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
            'schemaKey': 'Dandiset',
            'description': faker.Faker().sentence(),
            'access': [
                {
                    'schemaKey': 'AccessRequirements',
                    'status': AccessType.EmbargoedAccess.value
                    if self.dandiset.embargoed
                    else AccessType.OpenAccess.value,
                }
            ],
            'contributor': [
                {
                    'name': f'{faker.Faker().last_name()}, {faker.Faker().first_name()}',
                    'roleName': ['dcite:ContactPerson'],
                    'email': faker.Faker().email(),
                    'schemaKey': 'Person',
                }
            ],
            'license': ['spdx:CC0-1.0'],
        }
        # Remove faked data that might conflict with the schema types
        for key in ['about']:
            if key in metadata:
                del metadata[key]
        return metadata


class DraftVersionFactory(BaseVersionFactory):
    class Meta:
        model = Version

    version = 'draft'


class PublishedVersionFactory(BaseVersionFactory):
    class Meta:
        model = Version

    @classmethod
    def _create(cls, *args, **kwargs):
        version: Version = super()._create(*args, **kwargs)
        version.doi = f'10.80507/dandi.{version.dandiset.identifier}/{version.version}'
        now = datetime.datetime.now(datetime.UTC)
        version.metadata = {
            **version.metadata,
            'publishedBy': version.published_by(now),
            'datePublished': now.isoformat(),
        }
        version.save()
        return version


class AssetBlobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetBlob

    blob_id = factory.Faker('uuid4')
    size = 100

    @factory.lazy_attribute
    def blob(self):
        return django_files.File(
            file=django_files.base.ContentFile(faker.Faker().binary(self.size)).file,
            name=Upload.object_key(self.blob_id),
        )

    @factory.lazy_attribute
    def sha256(self):
        h = hashlib.sha256()
        h.update(self.blob.read())
        self.blob.seek(0)
        return h.hexdigest()

    @factory.lazy_attribute
    def etag(self):
        etagger = DandiETag(self.size)
        for part in etagger._part_gen:
            etagger.update(self.blob.read(part.size))

        self.blob.seek(0)
        return etagger.as_str()


class EmbargoedAssetBlobFactory(AssetBlobFactory):
    class Meta:
        model = AssetBlob

    embargoed = True


class DraftAssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Asset

    path = factory.Faker('file_path', absolute=False, extension='nwb')
    blob = factory.SubFactory(AssetBlobFactory)

    @factory.lazy_attribute
    def metadata(self):
        metadata = {
            **faker.Faker().pydict(value_types=['str', 'float', 'int']),
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
            'encodingFormat': 'application/x-nwb',
            'schemaKey': 'Asset',
        }
        # Remove faked data that might conflict with the schema types
        for key in ['approach', 'about', 'name']:
            if key in metadata:
                del metadata[key]
        return metadata


class PublishedAssetFactory(DraftAssetFactory):
    @classmethod
    def _create(cls, *args, **kwargs):
        asset: Asset = super()._create(*args, **kwargs)
        asset.status = Asset.Status.VALID  # published assets are always valid
        asset.save()
        publish_asset(asset=asset)
        asset.refresh_from_db()
        return asset


class UploadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Upload

    upload_id = factory.Faker('uuid4')
    multipart_upload_id = factory.Faker('uuid4')
    blob = factory.django.FileField(data=factory.Faker('binary', length=100))
    dandiset = factory.SubFactory(DandisetFactory)

    @factory.lazy_attribute
    def size(self):
        return self.blob.size

    @factory.lazy_attribute
    def etag(self):
        h = hashlib.md5()
        h.update(self.blob.read())
        self.blob.seek(0)
        return h.hexdigest()


class EmbargoedUploadFactory(UploadFactory):
    class Meta:
        model = Upload

    embargoed = True
