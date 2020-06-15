from bson.objectid import ObjectId

from girder.api.describe import getCurrentUser
from girder.constants import AccessType
from girder.exceptions import AccessException
from girder.models.folder import Folder
from girder.models.user import User


from .util import find_dandiset_by_identifier


def _get_lock(identifier):
    """
    Return the current owner of the lock on the given dandiset.

    If there is no lock, None is returned.
    """
    dandiset_folder = find_dandiset_by_identifier(identifier)
    if dandiset_folder is None or "locked" not in dandiset_folder:
        return None
    return str(dandiset_folder["locked"])


def _set_lock(identifier, user):
    """
    Set the lock on the given dandiset to the given user.

    The user must have admin access on the dandiset.
    """
    dandiset_folder = find_dandiset_by_identifier(identifier)
    Folder().requireAccess(dandiset_folder, user=user, level=AccessType.ADMIN)
    dandiset_folder["locked"] = user["_id"]
    Folder().save(dandiset_folder)


def _remove_lock(identifier):
    """Remove the lock from the dandiset if it is present."""
    dandiset_folder = find_dandiset_by_identifier(identifier)
    if "locked" in dandiset_folder:
        del dandiset_folder["locked"]
        Folder().save(dandiset_folder)


def has_lock(identifier, user):
    """
    Return whether or not the given user currently owns the lock on the given dandiset.

    If user is None, returns whether or not there is no lock on the given dandiset.
    """
    user_id = str(user["_id"]) if user is not None else None
    return _get_lock(identifier) == user_id


def require_lock(identifier, user):
    """
    Require that the user has the lock on the given dandiset.

    If user is None, then it will verify that there is no lock.
    This method should be used to ensure that a lock is present.
    Note the different between this method and require_access.
    """
    if not has_lock(identifier, user):
        locked_by = get_lock_owner(identifier)
        if locked_by is not None:
            owner_str = f"{locked_by['firstName']} {locked_by['lastName']}"
            raise AccessException(f"Dandiset {identifier} is currently locked by {owner_str}")
        else:
            raise AccessException(f"Dandiset {identifier} is currently unlocked")


def require_access(identifier, user):
    """
    Require that the user either have the lock, or no lock is present.

    This method should be used to determine if a user can modify a dandiset.
    """
    if (not has_lock(identifier, None)) and (not has_lock(identifier, user)):
        locked_by = get_lock_owner(identifier)
        owner_str = f"{locked_by['firstName']} {locked_by['lastName']}"
        raise AccessException(f"Dandiset {identifier} is currently locked by {owner_str}")


def lock(identifier, user):
    """
    Lock the given dandiset to the given user.

    The dandiset must be unlocked.
    """
    require_lock(identifier, None)
    _set_lock(identifier, user)


def unlock(identifier, user):
    """
    Unlock the given dandiset.

    The given user must currently have the lock on the dandiset.
    """
    require_lock(identifier, user)
    _remove_lock(identifier)


def get_lock_owner(identifier):
    """Return the user who currently has the lock on the resource, or None if there is no lock."""
    lock_id = _get_lock(identifier)
    if lock_id is None:
        return None
    return User().findOne(ObjectId(lock_id))


def folder_save_listener(event):
    """
    Listen to folder save events to enforce locking.

    If the folder has been locked by someone other than the current user,
    an exception is thrown.
    """
    try:
        identifier = event.info["meta"]["dandiset"]["identifier"]
        require_access(identifier, getCurrentUser())
    except KeyError:
        # This event is on a non-dandiset folder, no locking is required
        pass


def upload_assetstore_listener(event):
    """
    Listen to upload assetstore events to enforce locking.

    These events occur before files are uploaded.
    If the root dandiset folder has been locked by someone other than the current user,
    an exception is thrown.
    """
    thing = event.info["resource"]
    while thing["parentCollection"] != "collection":
        thing = Folder().findOne(thing["parentId"])
    try:
        identifier = thing["meta"]["dandiset"]["identifier"]
        require_access(identifier, getCurrentUser())
    except KeyError:
        # This event is on a non-dandiset folder, no locking is required
        pass
