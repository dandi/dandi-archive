# flake8: noqa
"""
Create placeholder Django users for as many dandiset owners in Girder as possible.

Run me locally:
python manage.py runscript create_placeholder_users --script-args http://localhost:8080/api/v1 username password
Run me in production:
python manage.py runscript create_placeholder_users --script-args http://girder.dandiarchive.org/api/v1 username password

Only dandisets that exist in both Girder and Django are considered, all others are ignored.
This is determined by matching the Girder dandiset identifier with the identifier stored in the Django metadata.
Once dandisets are matched, the script will do the following for each Girder owner:
 * Check if a Django user exists with the Girder owner's email
 * If not, check if a Django user exists with the Girder owner's email, prepended with 'placeholder_'
 * If not, create a placeholder user in Django
It will then assign ownership of the dandiset to the user.
This prevents placeholders from being created for users who already exist or have already been placeholdered.
"""
from django.contrib.auth.models import User
from girder_client import GirderClient
from guardian.shortcuts import assign_perm

from dandiapi.api.models import Dandiset, Version


def get_girder_dandisets(gc):
    dandisets = {}
    for dandiset in gc.get('/dandi'):
        identifier = dandiset['meta']['dandiset']['identifier']
        dandisets[identifier] = [
            user['id'] for user in dandiset['access']['users'] if user['level'] == 2
        ]
    return dandisets


def find_or_find_placeholder_or_create_placeholder(girder_user):
    email = girder_user['email']
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        pass
    try:
        return User.objects.get(email=f'placeholder_{email}')
    except User.DoesNotExist:
        print(f'Creating new placeholder user placeholder_{email}')
        user = User(
            username=girder_user['login'],
            first_name=girder_user['firstName'],
            last_name=girder_user['lastName'],
            email=f'placeholder_{email}',
        )
        user.save()
        return user


def migrate_dandiset(gc, dandiset, user_ids):
    for user_id in user_ids:
        girder_user = gc.get(f'user/{user_id}')
        django_user = find_or_find_placeholder_or_create_placeholder(girder_user)
        if not django_user.has_perm('owner', dandiset):
            print(f'Assigning ownership of {dandiset.identifier} to {django_user}')
            assign_perm('owner', django_user, dandiset)


def migrate(gc):
    girder_dandisets = get_girder_dandisets(gc)
    for dandiset_identifier in girder_dandisets:
        # Do not use the dandiset identifier, it is an autoincremented primary key
        # and cannot be trusted.
        # We are also assuming that no two dandisets will have metadata with the same identifier.
        dandi_id = f'DANDI:{dandiset_identifier}'
        version = Version.objects.filter(metadata__metadata__identifier=dandi_id).first()
        if version is None:
            print(f'Dandiset {dandiset_identifier} does not exist in Django')
            continue
        print(f'Found dandiset {dandiset_identifier} in both Girder and Django')
        user_ids = girder_dandisets[dandiset_identifier]
        migrate_dandiset(gc, version.dandiset, user_ids)


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

    migrate(gc)
