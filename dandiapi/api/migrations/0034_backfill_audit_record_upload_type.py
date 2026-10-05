from __future__ import annotations

from django.db import migrations

# All zarr chunk uploads predating multipart zarr upload were single-part, so mark the
# existing audit records as such.
BACKFILL_UPLOAD_TYPE = """
UPDATE api_auditrecord
SET details = jsonb_set(details, '{upload_type}', '"singlepart"')
WHERE record_type = 'upload_zarr_chunks'
"""

REMOVE_UPLOAD_TYPE = """
UPDATE api_auditrecord
SET details = details - 'upload_type'
WHERE record_type = 'upload_zarr_chunks'
"""


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0033_remove_upload_embargoed'),
    ]

    operations = [
        migrations.RunSQL(sql=BACKFILL_UPLOAD_TYPE, reverse_sql=REMOVE_UPLOAD_TYPE),
    ]
