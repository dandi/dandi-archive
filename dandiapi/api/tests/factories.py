import datetime
import hashlib
import random
from uuid import uuid4

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
import factory
import faker

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


class VersionMetadataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = VersionMetadata

    @factory.lazy_attribute
    def metadata(self):
        return {
            'schemaVersion': '0.3.1',
            # Inject some randomness so that duplicate metadatas don't violate DB constraints
            'description': f'description {random.random()}',
            'contributor': [{}],
            'license': ['spdx:CC0-1.0'],
            'publishedBy': {
                'id': uuid4().urn,
                'name': 'DANDI publish',
                'startDate': '2021-05-18T19:58:39.310338-04:00',
                'endDate': '2021-05-18T19:58:39.310361-04:00',
                'wasAssociatedWith': [
                    {
                        'id': 'RRID:SCR_017571',
                        'name': 'DANDI API',
                        'version': '0.1.0',
                        'schemaKey': 'Software',
                    }
                ],
                'schemaKey': 'PublishActivity',
            },
            'datePublished': str(datetime.datetime.now()),
            'assetsSummary': {
                'numberOfBytes': 1,
                'numberOfFiles': 1,
                'dataStandard': [],
                'approach': [],
                'measurementTechnique': [],
                'species': [],
            },
        }

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
        return h.hexdigest()

    @factory.lazy_attribute
    def size(self):
        return len(self.blob.read())


class AssetMetadataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetMetadata

    @factory.lazy_attribute
    def metadata(self):
        return {
            'schemaVersion': '0.3.1',
            'encodingFormat': 'application/x-nwb',
            'publishedBy': {
                'id': uuid4().urn,
                'name': 'DANDI publish',
                'startDate': '2021-05-18T19:58:39.310338-04:00',
                'endDate': '2021-05-18T19:58:39.310361-04:00',
                'wasAssociatedWith': [
                    {
                        'id': 'RRID:SCR_017571',
                        'name': 'DANDI API',
                        'version': '0.1.0',
                        'schemaKey': 'Software',
                    }
                ],
                'schemaKey': 'PublishActivity',
            },
            'datePublished': str(datetime.datetime.now()),
            # Inject some randomness so that duplicate metadatas don't violate DB constraints
            'description': f'description {random.random()}',
        }


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
