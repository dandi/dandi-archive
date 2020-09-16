import contextlib
from typing import Any, Dict, Iterator, List

import factory

from dandiapi.api.girder import GirderClient, GirderFile


class _GirderClientFolderFactory(factory.DictFactory):
    _id = factory.Faker('hexify', text='^' * 24)
    name = factory.Faker('bothify', text='sub-????????##')
    # A basic folder has a 'meta' key with no content
    meta = factory.Dict({})


class _GirderClientDraftFolderFactory(_GirderClientFolderFactory):
    name = factory.Faker('numerify', text='#' * 6)
    meta = factory.Dict(
        {
            'dandiset': factory.Dict(
                {'name': factory.Faker('sentence'), 'description': factory.Faker('paragraph')}
            )
        }
    )


class _GirderClientItemFactory(factory.DictFactory):
    _id = factory.Faker('hexify', text='^' * 24)
    name = factory.Faker('file_name', extension='nwb')
    meta = factory.Dict({})


class _GirderClientFileFactory(factory.DictFactory):
    _id = factory.Faker('hexify', text='^' * 24)
    size = factory.Faker('random_int', min=10, max=100)


class MockGirderClient(GirderClient):
    def __init__(self, authenticate: bool = False, **kwargs) -> None:
        super().__init__(authenticate=False, **kwargs)

    def get_json(self, *args, **kwargs) -> Any:
        raise NotImplementedError

    def get_folder(self, folder_id: str) -> Dict:
        if folder_id == 'magic_draft_folder_id':
            return _GirderClientDraftFolderFactory()
        else:
            return _GirderClientFolderFactory()

    def get_subfolders(self, folder_id: str) -> List[Dict]:
        return _GirderClientFolderFactory.build_batch(1)

    def get_items(self, folder_id: str) -> List[Dict]:
        return _GirderClientItemFactory.build_batch(1)

    def get_item_files(self, item_id: str) -> List[Dict]:
        file_size = len(b'Fake DANDI file content.Part 2.')
        return _GirderClientFileFactory.build_batch(1, size=file_size)

    @contextlib.contextmanager
    def iter_file_content(self, file_id: str) -> Iterator[bytes]:
        yield iter([b'Fake DANDI file content.', b'Part 2.'])

    @contextlib.contextmanager
    def dandiset_lock(self, dandiset_identifier: str) -> None:
        yield


class GirderFileFactory(factory.Factory):
    class Meta:
        model = GirderFile

    girder_id = factory.Faker('hexify', text='^' * 24)
    path = factory.Faker('file_path', extension='nwb')
    metadata = factory.Dict({})
    size = factory.Faker('random_int', min=10, max=100)
