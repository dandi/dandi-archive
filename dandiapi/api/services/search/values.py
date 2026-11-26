"""List the values that search operators over ``assetsSummary`` can match.

The web UI uses these to suggest values after ``species:`` and the like.
"""

from __future__ import annotations

from django.db import connection

from dandiapi.api.models import Dandiset, Version

# The same operator -> jsonpath map the filters search, so suggestions always
# come from where the operator looks.
from dandiapi.api.services.search.filters import _SUMMARY_PATH_OPS

# The operators whose values come from assetsSummary, and so can be listed.
SUMMARY_OPERATORS = frozenset(_SUMMARY_PATH_OPS)


def summary_operator_values(operator: str) -> list[dict[str, str | int]]:
    """List the values an assetsSummary operator can match, most common first.

    Each entry is ``{'value': ..., 'dandisets': n}``, where ``n`` counts the
    dandisets with that value in any version's assetsSummary: the same versions
    and paths the operator searches. Only open dandisets are counted, so the
    list never reveals metadata of embargoed ones.
    """
    path = _SUMMARY_PATH_OPS[operator]
    # Table names come from the models, not from user input; the jsonpath and
    # the embargo status are bound as parameters.
    sql = f"""
        SELECT value #>> '{{}}' AS value, COUNT(DISTINCT version.dandiset_id) AS dandisets
        FROM {Version._meta.db_table} AS version
        JOIN {Dandiset._meta.db_table} AS dandiset ON dandiset.id = version.dandiset_id
        CROSS JOIN LATERAL jsonb_path_query(version.metadata, %s::jsonpath) AS value
        WHERE dandiset.embargo_status = %s
          AND jsonb_typeof(value) = 'string'
          AND value #>> '{{}}' <> ''
        GROUP BY 1
        ORDER BY dandisets DESC, value
    """  # noqa: S608
    with connection.cursor() as cursor:
        cursor.execute(sql, [path, Dandiset.EmbargoStatus.OPEN])
        return [{'value': value, 'dandisets': count} for value, count in cursor.fetchall()]
