from __future__ import annotations

import sys


def _patch_dandischema_if_needed() -> None:
    """
    Monkey-patches a `conf` module into `dandischema` if needed.

    To allow dandi-archive to release without a coordinated release of dandi-schema in regard to
    the vendorization effort implemented in https://github.com/dandi/dandi-schema/pull/294.
    """
    try:
        import dandischema.conf
    except ImportError as e:
        import importlib.metadata

        import dandischema
        from packaging.version import Version

        from . import _dandischema_conf_stub

        # Confirm that dandischema version is before the inclusion of
        # https://github.com/dandi/dandi-schema/pull/294
        base_vendorizable_dandi_schema_version = Version('0.12.0')
        dandi_schema_version = Version(importlib.metadata.version('dandischema'))
        if dandi_schema_version >= base_vendorizable_dandi_schema_version:
            raise ImportError(
                f'Failed to import `dandischema.conf` despite '
                f'dandischema>={base_vendorizable_dandi_schema_version}'
            ) from e

        # Patch in the stub conf module for older version of dandischema
        sys.modules['dandischema.conf'] = _dandischema_conf_stub  # Ensure import statements work
        dandischema.conf = _dandischema_conf_stub  # Ensure attribute access works
