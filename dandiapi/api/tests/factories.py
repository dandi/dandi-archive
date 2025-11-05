from __future__ import annotations

import datetime
import hashlib
from typing import Any

from allauth.socialaccount.models import SocialAccount
from dandischema.conf import get_instance_config
from dandischema.models import AccessType
from django.conf import settings
from django.contrib.auth.models import User
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
from dandiapi.api.services.metadata import get_default_license
from dandiapi.api.services.permissions.dandiset import add_dandiset_owner


class UserMetadataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserMetadata

    status = UserMetadata.Status.APPROVED.value


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

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
    def extra_data(self) -> dict[str, Any]:
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
        skip_postgeneration_save = True

    @factory.post_generation
    def owners(self, create: bool, extracted: list[User] | None) -> None:  # noqa: FBT001
        if not create:
            return
        if extracted is None:
            extracted = []
        for user in extracted:
            add_dandiset_owner(dandiset=self, user=user)


class BaseVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Version
        skip_postgeneration_save = True
        abstract = True

    dandiset = factory.SubFactory(DandisetFactory)
    name = factory.Faker('sentence')
    # Don't use "Version.next_published_version" to create versions, as that will require
    # additional database queries.
    version = factory.Sequence(
        lambda n: Version.datetime_to_version(
            datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=n)
        )
    )
    status = Version.Status.PENDING

    @factory.lazy_attribute
    def metadata(self) -> dict:
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
            'license': [get_default_license()],
        }
        # Remove faked data that might conflict with the schema types
        for key in ['about']:
            metadata.pop(key, None)
        if self.status == Version.Status.PUBLISHED:
            now = datetime.datetime.now(datetime.UTC)
            metadata.update(
                {
                    'publishedBy': Version.published_by(now),
                    'datePublished': now.isoformat(),
                }
            )
        return metadata

    @factory.post_generation
    def assets(self, create: bool, extracted: list[Asset]) -> None:  # noqa: FBT001
        if not create or not extracted:
            return
        self.assets.add(*extracted)


class DraftVersionFactory(BaseVersionFactory):
    version = 'draft'


class PublishedVersionFactory(BaseVersionFactory):
    doi = factory.LazyAttribute(
        lambda self: f'{get_instance_config().doi_prefix}/'
        f'{get_instance_config().instance_name}.'
        f'{self.dandiset.identifier}/{self.version}'
    )
    status = Version.Status.PUBLISHED


class AssetBlobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetBlob
        skip_postgeneration_save = True

    blob_id = factory.Faker('uuid4')

    # Override this with:
    #   AssetBlobFactory.create(blob__filename='...')  # for a specific file name
    #   AssetBlobFactory.create(blob__data=b'...')  # for specific data
    #   AssetBlobFactory.create(blob__data__length=...)  # for random data of a specific size
    blob = factory.django.FileField(
        filename=factory.Faker('file_name', extension='dat'),
        data=factory.Faker('binary', length=100),
    )
    # Don't try to set "AssetBlobFactory.create(size=...)" directly, let it be read from the blob
    size = factory.LazyAttribute(lambda self: len(self.blob))

    @factory.lazy_attribute
    def sha256(self) -> str:
        sha256 = hashlib.sha256(self.blob.read()).hexdigest()
        self.blob.seek(0)
        return sha256

    @factory.lazy_attribute
    def etag(self) -> str:
        # In production, files would be uploaded with a multipart ETag:
        # etagger = DandiETag(self.size)
        # etagger.partial_update(self.blob.read())
        # self.blob.seek(0)
        # return etagger.as_str()
        # In tests, the factories use "Storage.save", which uses S3 put_object,
        # resulting in an MD5 ETag:
        etag = hashlib.md5(self.blob.read()).hexdigest()
        self.blob.seek(0)
        return etag

    @classmethod
    def _after_postgeneration(cls, obj: AssetBlob, create: bool, results=None) -> None:  # noqa: FBT001
        super()._after_postgeneration(obj, create, results)
        if not create:
            return
        if obj.embargoed:
            obj.blob.storage.put_tags(obj.blob.name, {'embargoed': 'true'})


class EmbargoedAssetBlobFactory(AssetBlobFactory):
    embargoed = True


class DraftAssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Asset

    path = factory.Faker('file_path', absolute=False, extension='nwb')
    blob = factory.SubFactory(AssetBlobFactory)
    published = False

    @factory.lazy_attribute
    def metadata(self) -> dict:
        metadata = {
            **faker.Faker().pydict(value_types=['str', 'float', 'int']),
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
            'encodingFormat': 'application/x-nwb',
            'schemaKey': 'Asset',
        }
        # Remove faked data that might conflict with the schema types
        for key in ['approach', 'about', 'name']:
            metadata.pop(key, None)
        return metadata


class PublishedAssetFactory(DraftAssetFactory):
    published = True
    status = Asset.Status.VALID  # published assets are always valid

    @classmethod
    def _create(cls, model_class: type[Asset], *args, **kwargs) -> Asset:
        # Call "_build" to create without saving, as a save won't be valid until the metadata is set
        asset: Asset = super()._build(model_class, *args, **kwargs)
        asset.metadata = asset.published_metadata()
        asset.save()
        return asset


class UploadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Upload
        skip_postgeneration_save = True

    upload_id = factory.Faker('uuid4')
    multipart_upload_id = factory.Faker('pystr', min_chars=32, max_chars=96)

    blob = factory.django.FileField(
        filename=factory.Faker('file_name', extension='dat'),
        data=factory.Faker('binary', length=100),
    )
    size = factory.LazyAttribute(lambda self: len(self.blob))

    dandiset = factory.SubFactory(DandisetFactory)

    @factory.lazy_attribute
    def etag(self) -> str:
        # In production, files would be uploaded with a multipart ETag:
        # etagger = DandiETag(self.size)
        # etagger.partial_update(self.blob.read())
        # self.blob.seek(0)
        # return etagger.as_str()
        # In tests, the factories use "Storage.save", which uses S3 put_object,
        # resulting in an MD5 ETag:
        etag = hashlib.md5(self.blob.read()).hexdigest()
        self.blob.seek(0)
        return etag

    @classmethod
    def _after_postgeneration(cls, obj: Upload, create: bool, results=None) -> None:  # noqa: FBT001
        super()._after_postgeneration(obj, create, results)
        if not create:
            return
        if obj.embargoed:
            obj.blob.storage.put_tags(obj.blob.name, {'embargoed': 'true'})


class EmbargoedUploadFactory(UploadFactory):
    embargoed = True
