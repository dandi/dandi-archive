from __future__ import annotations

from io import StringIO

from django.core.files.storage import default_storage


# This test will fail if AWS_S3_FILE_OVERWRITE == False
def test_file_overwrite():
    path = 'foobar.txt'
    a = default_storage.save(path, StringIO('something'))
    b = default_storage.save(path, StringIO('something else'))
    assert a == b
