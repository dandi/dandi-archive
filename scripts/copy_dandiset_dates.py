# flake8: noqa
"""
Copy the created and modified dates from the girder instance to the django instance.

Run me locally:
python manage.py runscript copy_dandiset_dates --script-args http://localhost:8080/api/v1 username password
Run me in production:
python manage.py runscript copy_dandiset_dates --script-args http://girder.dandiarchive.org/api/v1 username password

Only dandisets that exist in both Girder and Django are considered, all others are ignored.
This is determined by matching the Girder dandiset identifier with the identifier stored in the Django metadata.
"""
from datetime import datetime

from girder_client import GirderClient

from dandiapi.api.models import Dandiset, Version


def get_girder_dandisets(gc):
    dandisets = {}
    for dandiset in gc.get('/dandi'):
        identifier = dandiset['meta']['dandiset']['identifier']
        dandisets[identifier] = (
            datetime.fromisoformat(dandiset['created']),
            datetime.fromisoformat(dandiset['updated']),
        )
    return dandisets


def copy_dates(gc: GirderClient):
    girder_dandisets = get_girder_dandisets(gc)
    for dandiset_identifier in girder_dandisets:
        created, _modified = girder_dandisets[dandiset_identifier]
        try:
            dandiset = Dandiset.objects.get(id=int(dandiset_identifier))
        except Dandiset.DoesNotExist:
            print(f'Could not find dandiset {dandiset_identifier}')
            continue
        try:
            version = dandiset.versions.get(version='draft')
        except Version.DoesNotExist:
            print(f'No draft for dandiset {dandiset_identifier}')
            continue
        dandiset.created = created
        version.created = created
        # We are not copying modified because the migration process counts
        # as modifying all existing dandisets.
        # dandiset.modified = modified
        # version.modified = modified

        # Do not trigger the auto modified field
        dandiset.save(update_modified=False)
        version.save(update_modified=False)

        print(f'Copied created date for {dandiset_identifier}')


def run(*args):
    if len(args) != 3:
        print(
            'Usage: python manage.py runscript create_placeholder_users --script-args {api_url} {username} {password}'
        )
        return
    api_url = args[0]
    username = args[1]
    password = args[2]

    gc = GirderClient(apiUrl=api_url)
    gc.authenticate(username, password)

    copy_dates(gc)
