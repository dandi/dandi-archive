import contextlib
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List

from httpx import Client


class GirderError(Exception):
    pass


@dataclass
class GirderFile:
    girder_id: str
    path: str
    metadata: Dict[str, Any]
    size: int


class GirderClient(Client):
    def __init__(self, authenticate=False, **kwargs):
        girder_api_url = None
        girder_api_key = None
        if not girder_api_url.endswith('/'):
            girder_api_url += '/'

        kwargs.setdefault('base_url', girder_api_url)
        super().__init__(**kwargs)

        if not authenticate:
            return

        # Fetch the token using the API key
        resp = self.post('api_key/token', params={'key': girder_api_key})
        if resp.status_code != 200:
            raise GirderError('Failed to authenticate with Girder')
        token = resp.json()['authToken']['token']

        # Include the token header for all subsequent requests
        self.headers = {'Girder-Token': token}

    def get_json(self, *args, **kwargs) -> Any:
        resp = self.get(*args, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def get_folder(self, folder_id: str) -> Dict:
        return self.get_json(f'folder/{folder_id}')

    def get_subfolders(self, folder_id: str) -> List[Dict]:
        return self.get_json(
            'folder', params={'parentId': folder_id, 'parentType': 'folder', 'limit': 0}
        )

    def get_items(self, folder_id: str) -> List[Dict]:
        return self.get_json('item', params={'folderId': folder_id, 'limit': 0})

    def get_item_files(self, item_id: str) -> List[Dict]:
        return self.get_json(f'item/{item_id}/files')

    @contextlib.contextmanager
    def iter_file_content(self, file_id: str) -> Iterator[bytes]:
        with self.stream('GET', f'file/{file_id}/download') as resp:
            resp.raise_for_status()
            yield resp.iter_bytes()

    @contextlib.contextmanager
    def dandiset_lock(self, dandiset_identifier: str) -> None:
        resp = self.post(f'dandi/{dandiset_identifier}/lock')
        if resp.status_code != 200:
            raise GirderError(f'Failed to lock dandiset {dandiset_identifier}')
        try:
            yield
        finally:
            resp = self.post(f'dandi/{dandiset_identifier}/unlock')
            if resp.status_code != 200:
                raise GirderError(f'Failed to unlock dandiset {dandiset_identifier}')

    def files_in_folder(self, folder_id: str, current_path: str = '/') -> Iterator[GirderFile]:
        for item in self.get_items(folder_id):
            file_list = self.get_item_files(item['_id'])
            if len(file_list) != 1:
                raise GirderError(f'Found {len(file_list)} files in item {item["_id"]}')

            f = file_list[0]
            if f['size'] == 0:
                raise GirderError(f'Found empty file {f["_id"]}')

            yield GirderFile(
                girder_id=f['_id'],
                # Use item name instead of file name, since it's more likely to reflect an
                # explicit rename operation in Girder
                path=f'{current_path}{item["name"]}',
                metadata=item['meta'],
                size=f['size'],
            )

        for subfolder in self.get_subfolders(folder_id):
            yield from self.files_in_folder(subfolder['_id'], f'{current_path}{subfolder["name"]}/')
