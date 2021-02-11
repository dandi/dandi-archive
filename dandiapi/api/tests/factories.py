import hashlib

from django.contrib.auth.models import User
import factory

from dandiapi.api.models import (
    Asset,
    AssetBlob,
    AssetMetadata,
    Dandiset,
    Validation,
    Version,
    VersionMetadata,
)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class DandisetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Dandiset


class VersionMetadataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = VersionMetadata

    metadata = factory.Faker('pydict', value_types=['str', 'float', 'int'])
    name = factory.Faker('sentence')


class BaseVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    dandiset = factory.SubFactory(DandisetFactory)
    metadata = factory.SubFactory(VersionMetadataFactory)


# class VersionFactory(BaseVersionFactory):
#     class Meta:
#         model = Version

#     dandiset = factory.SubFactory(DandisetFactory)


class DraftVersionFactory(BaseVersionFactory):
    class Meta:
        model = Version

    version = 'draft'


class PublishedVersionFactory(BaseVersionFactory):
    class Meta:
        model = Version


class AssetBlobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetBlob

    blob = factory.django.FileField(data=b'somefilebytes')

    @factory.lazy_attribute
    def sha256(self):
        h = hashlib.sha256()
        h.update(b'somefilebytes')
        return h.hexdigest()


class AssetMetadataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetMetadata

    metadata = factory.Faker('pydict', value_types=['str', 'float', 'int'])


class AssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Asset

    path = factory.Faker('file_path', extension='nwb')
    version = factory.SubFactory(DraftVersionFactory)
    metadata = factory.SubFactory(AssetMetadataFactory)
    blob = factory.SubFactory(AssetBlobFactory)


class ValidationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Validation

    blob = factory.django.FileField(data=b'validationbytes')

    @factory.lazy_attribute
    def sha256(self):
        h = hashlib.sha256()
        h.update(b'validationbytes')
        return h.hexdigest()

    state = 'SUCCEEDED'
    error = factory.Faker('sentence')
