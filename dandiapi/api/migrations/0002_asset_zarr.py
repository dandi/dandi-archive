from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0001_initial_v2'),
        ('zarr', '0001_initial_v2'),
        # Merge the orphan api.0001_stagingapplication
        ('api', '0001_stagingapplication'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='asset',
            name='exactly-one-blob',
        ),
        migrations.AddField(
            model_name='asset',
            name='zarr',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assets',
                to='zarr.zarrarchive',
            ),
        ),
        migrations.AddConstraint(
            model_name='asset',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ('blob__isnull', True),
                        ('embargoed_blob__isnull', True),
                        ('zarr__isnull', False),
                    ),
                    models.Q(
                        ('blob__isnull', True),
                        ('embargoed_blob__isnull', False),
                        ('zarr__isnull', True),
                    ),
                    models.Q(
                        ('blob__isnull', False),
                        ('embargoed_blob__isnull', True),
                        ('zarr__isnull', True),
                    ),
                    _connector='OR',
                ),
                name='exactly-one-blob',
            ),
        ),
    ]
