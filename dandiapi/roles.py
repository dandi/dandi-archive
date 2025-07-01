from __future__ import annotations

from dandiapi.api.models.dandiset import DandisetPermissions

DANDISET_CREATOR_ROLE = 'owner'
DANDISET_ROLES = {
    'default': [
        DandisetPermissions.STAR_DANDISET,
    ],
    'owner': list(DandisetPermissions),
    'viewer': [
        DandisetPermissions.VIEW_DANDISET,
        DandisetPermissions.VIEW_DANDISET_ASSETS,
        DandisetPermissions.VIEW_DANDISET_VERSIONS,
        DandisetPermissions.VIEW_ZARR_ARCHIVE,
        DandisetPermissions.LIST_ZARR_ARCHIVE_FILES,
    ],
}


GLOBAL_ROLES = {'admin': list(DandisetPermissions)}
