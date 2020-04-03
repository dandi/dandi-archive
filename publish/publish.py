from dataclasses import dataclass
from hashlib import sha256
from json import JSONDecodeError
from tempfile import TemporaryFile
from typing import Any, Dict, List, TYPE_CHECKING

import boto3
from botocore.exceptions import ClientError  # type: ignore
import click
from httpx import Client, Response, stream
from tqdm import tqdm  # type: ignore
from yaml import dump

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client  # noqa

BASE_URL = 'https://girder.dandiarchive.org/api/v1/'
S3_BUCKET = 'dandi'
S3_PREFIX = 'dandisets'
S3_ENDPOINT_URL = 'http://localhost:9000'


class DandiSetLoadError(Exception):
    pass


class DandiClient(Client):
    def __init__(self, token=None, **kwargs):
        kwargs.setdefault('base_url', BASE_URL)
        if token:
            kwargs.setdefault('headers', {'Girder-Token': token})
        super().__init__(**kwargs)


def _get_json(response: Response) -> Any:
    if response.status_code != 200:
        raise DandiSetLoadError(f'Girder returned status code {response.status_code}')
    try:
        return response.json()
    except JSONDecodeError:
        raise DandiSetLoadError(f'Girder returned non-json response: {repr(response.content)}')


@dataclass
class DandiFile:
    girder_id: str
    name: str
    url: str
    metadata: Dict[str, Any]
    size: int

    def publish(self, s3: 'S3Client', prefix: str):
        nwb_key = f'{prefix}/{self.name}'
        with TemporaryFile('r+b') as nwb, stream('GET', self.url) as response:
            click.echo(f'Downloading {self.name}...')
            response.raise_for_status()
            hash = sha256()
            with tqdm(total=self.size, unit_scale=True, unit_divisor=1024, unit='B', leave=False) as bar:
                i = 0
                for chunk in response.iter_bytes():
                    if i > 10:
                        break
                    if chunk:
                        i += 1
                        hash.update(chunk)
                        bar.update(len(chunk))
                        nwb.write(chunk)

            click.echo(hash.hexdigest())
            click.echo(f'Uploading {self.name}...')
            nwb.seek(0)
            with tqdm(total=self.size, unit_scale=True, unit_divisor=1024, unit='B', leave=False) as bar:
                def callback(size):
                    bar.update(size)
                s3.upload_fileobj(
                    nwb,
                    S3_BUCKET,
                    nwb_key,
                    ExtraArgs={'ACL': 'public-read'},
                    Callback=callback,
                )


@dataclass
class DandiSubject:
    girder_id: str
    name: str
    files: List[DandiFile]

    @classmethod
    def load(cls, client: Client, girder_id: str, name: str) -> 'DandiSubject':
        items = _get_json(client.get(f'item', params={'folderId': str(girder_id), 'limit': 0}))
        files = []
        for item in items:
            file_list = _get_json(client.get(f'item/{item["_id"]}/files'))
            if len(file_list) != 1:
                raise DandiSetLoadError(f'Expected exactly one file per item not {len(file_list)}')
            f = file_list[0]
            files.append(
                DandiFile(
                    girder_id=f['_id'],
                    name=f['name'],
                    metadata=item['meta'],
                    url=f'{BASE_URL}file/{f["_id"]}/download',
                    size=f['size'],
                )
            )
        return cls(girder_id=girder_id, name=name, files=files)

    def publish(self, s3: 'S3Client', prefix: str):
        subject_prefix = f'{prefix}/{self.name}'
        for file in self.files:
            file.publish(s3, subject_prefix)


@dataclass
class DandiSet:
    girder_id: str
    dandi_id: str
    metadata: Dict[str, Any]
    subjects: List[DandiSubject]

    @classmethod
    def load(cls, client: Client, girder_id: str) -> 'DandiSet':
        dandiset_folder = _get_json(client.get(f'folder/{girder_id}'))
        subject_folders = _get_json(
            client.get(
                f'folder', params={'parentId': str(girder_id), 'parentType': 'folder', 'limit': 0}
            )
        )
        subjects = [DandiSubject.load(client, f['_id'], f['name']) for f in subject_folders]

        return cls(
            girder_id=girder_id,
            dandi_id=dandiset_folder['name'],
            metadata=dandiset_folder['meta'],
            subjects=subjects,
        )

    def s3_path(self, version):
        return f'{S3_PREFIX}/{self.dandi_id}/{version}'

    def _get_next_version(self, s3: 'S3Client') -> int:
        version = 1
        while True:
            try:
                s3.get_object(Bucket=S3_BUCKET, Key=f'{self.s3_path(version)}/dandiset.yaml')
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    return version
                raise
            version += 1

    def publish(self, s3: 'S3Client') -> str:
        version = self._get_next_version(s3)
        prefix = self.s3_path(version)

        for subject in self.subjects:
            subject.publish(s3, prefix)

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=f'{prefix}/dandiset.yaml',
            Body=dump(self.metadata).encode(),
            ACL='public-read',
        )
        return f's3://{S3_BUCKET}/{prefix}'


@click.command()
@click.argument('girder_id')
def publish_dandiset(girder_id: str):
    s3 = boto3.client('s3', endpoint_url=S3_ENDPOINT_URL)
    click.echo('Getting dandiset metadata...')
    with DandiClient() as client:
        dandiset = DandiSet.load(client, girder_id)
    click.echo(dandiset.publish(s3))


if __name__ == '__main__':
    publish_dandiset()
