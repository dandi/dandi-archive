import hashlib

from django.contrib.auth.models import User
import factory

from dandiapi.api.models import (
    Asset,
    AssetBlob,
    AssetMetadata,
    Dandiset,
    Upload,
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

    uuid = factory.Faker('uuid4')
    blob = factory.django.FileField(data=factory.Faker('binary', length=100))
    size = 13  # len(somefilebytes)

    @factory.lazy_attribute
    def sha256(self):
        h = hashlib.sha256()
        h.update(self.blob.read())
        self.blob.seek(0)
        return h.hexdigest()

    @factory.lazy_attribute
    def etag(self):
        h = hashlib.md5()
        h.update(self.blob.read())
        self.blob.seek(0)
        return h.hexdigest()

    @factory.lazy_attribute
    def size(self):
        return len(self.blob.read())


class AssetMetadataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetMetadata

    metadata = factory.Faker('pydict', value_types=['str', 'float', 'int'])


class AssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Asset

    path = factory.Faker('file_path', extension='nwb')
    metadata = factory.SubFactory(AssetMetadataFactory)
    blob = factory.SubFactory(AssetBlobFactory)


class UploadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Upload

    upload_id = factory.Faker('uuid4')
    multipart_upload_id = factory.Faker('uuid4')
    blob = factory.django.FileField(data=factory.Faker('binary', length=100))

    @factory.lazy_attribute
    def size(self):
        return self.blob.size

    @factory.lazy_attribute
    def etag(self):
        h = hashlib.md5()
        h.update(self.blob.read())
        self.blob.seek(0)
        return h.hexdigest()
