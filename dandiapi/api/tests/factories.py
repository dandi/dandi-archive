import hashlib

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
import factory
import faker

from dandiapi.api.models import Asset, AssetBlob, Dandiset, Upload, Version


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class SocialAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SocialAccount

    user = factory.SubFactory(UserFactory)
    uid = factory.Faker('sha1')

    @factory.lazy_attribute
    def extra_data(self):
        first_name = faker.Faker().first_name()
        last_name = faker.Faker().last_name()
        name = f'{first_name} {last_name}'
        return {
            'login': first_name,
            'name': name,
            'email': self.user.username,
        }


class DandisetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Dandiset


class BaseVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    dandiset = factory.SubFactory(DandisetFactory)
    name = factory.Faker('sentence')

    @factory.lazy_attribute
    def metadata(self):
        metadata = {
            **faker.Faker().pydict(value_types=['str', 'float', 'int']),
            'schemaVersion': '0.4.4',
            'description': faker.Faker().sentence(),
            'contributor': [{'roleName': ['dcite:ContactPerson']}],
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


class AssetBlobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetBlob

    blob_id = factory.Faker('uuid4')
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
        return f'{h.hexdigest()}-0'

    @factory.lazy_attribute
    def size(self):
        return len(self.blob.read())


class DraftAssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Asset

    path = factory.Faker('file_path', extension='nwb')
    blob = factory.SubFactory(AssetBlobFactory)

    @factory.lazy_attribute
    def metadata(self):
        metadata = {
            **faker.Faker().pydict(value_types=['str', 'float', 'int']),
            'schemaVersion': '0.4.4',
            'encodingFormat': 'application/x-nwb',
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
        asset.publish()
        asset.save()
        return asset


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
