import hashlib

from django.core.files.base import ContentFile
from django.core.files.storage import Storage

from dandiapi.api.checksum import calculate_sha256_checksum


def test_checksum(faker, storage: Storage):
    name = faker.file_name()
    sentence = bytes(faker.sentence(), 'utf-8')
    content = ContentFile(sentence)

    storage.save(name, content)

    h = hashlib.sha256()
    h.update(sentence)
    expected_sha256 = h.hexdigest()

    actual_sha256 = calculate_sha256_checksum(storage, name)

    assert actual_sha256 == expected_sha256
