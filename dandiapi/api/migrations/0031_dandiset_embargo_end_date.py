from __future__ import annotations

from datetime import date

from django.conf import settings
from django.db import migrations, models
from tqdm import tqdm


def populate_embargo_end_date(apps, schema_editor):
    Dandiset = apps.get_model('api', 'Dandiset')
    Version = apps.get_model('api', 'Version')

    # Ensure that all embargoed dandisets have a value in the embargoedUntil field
    problem_dandisets = Dandiset.objects.filter(
        embargo_status='EMBARGOED', versions__metadata__access__0__embargoedUntil__isnull=True
    )
    if problem_dandisets.exists():
        raise ValueError(
            f"Found {problem_dandisets.count()} dandisets without 'embargoedUntil' value!"
        )

    embargoed_dandisets = Dandiset.objects.filter(
        embargo_status='EMBARGOED', versions__metadata__access__0__embargoedUntil__isnull=False
    )
    for dandiset in tqdm(embargoed_dandisets.iterator(), total=embargoed_dandisets.count()):
        draft_version = Version.objects.get(dandiset=dandiset, version='draft')

        # embargoedUntil is stored as an ISO 8601 date string, e.g. "2025-01-01"
        embargoed_until = draft_version.metadata['access'][0]['embargoedUntil']

        try:
            dandiset.embargo_end_date = date.fromisoformat(embargoed_until)
            dandiset.save(update_fields=['embargo_end_date'])
        except (TypeError, ValueError):
            pass


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0030_alter_asset_path'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='dandiset',
            name='embargo_end_date',
            field=models.DateField(blank=True, default=None, null=True),
        ),
        migrations.RunPython(populate_embargo_end_date, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='dandiset',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ('embargo_end_date__isnull', False), ('embargo_status', 'OPEN'), _connector='OR'
                ),
                name='embargoed_dandiset_has_embargo_end_date',
            ),
        ),
    ]
