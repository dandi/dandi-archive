"""
Maps the identifiers of all Dandisets to the identifier listed in their metadata.

Identifier cycles are not addressed.
If you have Dandiset 000001 with {"identifier":000002} and Dandiset 000002
with {"identifier":000001}, manual intervention is required.
"""
from dandiapi.api.models.dandiset import Dandiset


def get_new_identifier(dandiset):
    metadata = dandiset.most_recent_version.metadata.metadata
    if 'identifier' not in metadata:
        print(f'Dandiset {dandiset.identifier} does not specify an identifier')
        return None
    try:
        identifier = int(metadata['identifier'])
    except ValueError:
        print(
            f'Dandiset {dandiset.identifier} has a bad metadata identifier {metadata["identifier"]}'
        )
        return None

    if 0 > identifier or identifier > 999999:
        print(
            f'Dandiset {dandiset.identifier} has a bad metadata identifier {metadata["identifier"]}'
        )
        return None

    if dandiset.id == identifier:
        # The identifier already matches
        return None

    if Dandiset.objects.filter(id=identifier):
        print(
            f'Dandiset {dandiset.identifier} cannot be copied because {identifier} already exists'
        )
        return None

    return identifier


def move(dandiset, new_id):
    # Grab the old dandiset's relevant information
    owners = dandiset.owners
    versions = list(dandiset.versions.all())

    # Create a new dandiset with the new identifier
    new_dandiset = Dandiset(id=new_id)
    new_dandiset.save()

    # Copy the owners
    new_dandiset.set_owners(owners)
    new_dandiset.save()

    # Copy the versions
    for version in versions:
        version.dandiset = new_dandiset
        version.save()

    # Delete the old dandiset
    dandiset.delete()


def move_if_necessary(dandiset):
    new_id = get_new_identifier(dandiset)
    if new_id:
        print(f'Copying dandiset {dandiset.identifier} to {new_id}')
        move(dandiset, new_id)
