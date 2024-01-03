from __future__ import annotations
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ProcessedS3Log',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'name',
                    models.CharField(
                        max_length=36,
                        validators=[
                            django.core.validators.RegexValidator(
                                '^\\d{4}-(\\d{2}-){5}[A-F0-9]{16}$'
                            )
                        ],
                    ),
                ),
                ('embargoed', models.BooleanField()),
            ],
            options={
                'unique_together': set(),
            },
        ),
        migrations.AddConstraint(
            model_name='processeds3log',
            constraint=models.UniqueConstraint(
                fields=('name', 'embargoed'), name='analytics_processeds3log_unique_name_embargoed'
            ),
        ),
    ]
