from __future__ import annotations

import factory

from dandiapi.api.tests.factories import DandisetFactory
from dandiapi.zarr.models import ZarrArchive


class ZarrArchiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ZarrArchive

    zarr_id = factory.Faker('uuid4')
    name = factory.Faker('catch_phrase')
    dandiset = factory.SubFactory(DandisetFactory)


class EmbargoedZarrArchiveFactory(ZarrArchiveFactory):
    embargoed = True
