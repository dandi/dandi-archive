import contextlib
from dataclasses import dataclass
from typing import Any, Dict, Iterator

from django.conf import settings
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
        girder_api_url = settings.DANDI_GIRDER_API_URL
        girder_api_key = settings.DANDI_GIRDER_API_KEY
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

    def files_in_folder(self, folder_id: str, current_path: str = '/') -> Iterator[GirderFile]:
        items = self.get_json('item', params={'folderId': str(folder_id), 'limit': 0})
        for item in items:
            file_list = self.get_json(f'item/{item["_id"]}/files')
            if len(file_list) != 1:
                raise GirderError(f'Found {len(file_list)} files in item {item["_id"]}')

            f = file_list[0]
            yield GirderFile(
                girder_id=f['_id'],
                # Use item name instead of file name, since it's more likely to reflect an
                # explicit rename operation in Girder
                path=f'{current_path}{item["name"]}',
                metadata=item['meta'],
                size=f['size'],
            )

        subfolders = self.get_json(
            'folder', params={'parentId': str(folder_id), 'parentType': 'folder', 'limit': 0}
        )
        for subfolder in subfolders:
            yield from self.files_in_folder(subfolder['_id'], f'{current_path}{subfolder["name"]}/')

    @contextlib.contextmanager
    def iter_file_content(self, file_id: str) -> Iterator[bytes]:
        with self.stream('GET', f'file/{file_id}/download') as resp:
            resp.raise_for_status()
            yield resp.iter_bytes()


@contextlib.contextmanager
def dandiset_lock(dandiset_id, client: GirderClient):
    resp = client.post(f'dandi/{dandiset_id}/lock')
    if (resp.status_code != 200):
        raise GirderError(f'Failed to lock dandiset {dandiset_id}')
    try:
        yield
    finally:
        resp = client.post(f'dandi/{dandiset_id}/unlock')
        if (resp.status_code != 200):
            raise GirderError(f'Failed to unlock dandiset {dandiset_id}')
