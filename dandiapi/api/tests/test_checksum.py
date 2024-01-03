from __future__ import annotations
import hashlib

from django.core.files.base import ContentFile
from django.core.files.storage import Storage


def test_checksum(faker, storage: Storage):
    name = faker.file_name()
    sentence = bytes(faker.sentence(), 'utf-8')
    content = ContentFile(sentence)

    storage.save(name, content)

    h = hashlib.sha256()
    h.update(sentence)
    expected_sha256 = h.hexdigest()

    actual_sha256 = storage.sha256_checksum(name)

    assert actual_sha256 == expected_sha256
