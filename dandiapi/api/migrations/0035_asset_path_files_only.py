from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0034_version_modification'),
    ]

    operations = [
        # Folders are no longer stored, and neither are the relations between asset paths.
        # This can't be reversed, as there's nothing to restore either of them from.
        migrations.DeleteModel(
            name='AssetPathRelation',
        ),
        migrations.RemoveConstraint(
            model_name='assetpath',
            name='consistent-leaf-paths',
        ),
        migrations.RunSQL('DELETE FROM api_assetpath WHERE asset_id IS NULL'),
        # All that remains are the paths of assets, each of which is already one file,
        # that has the size of its asset.
        migrations.RemoveField(
            model_name='assetpath',
            name='aggregate_files',
        ),
        migrations.RenameField(
            model_name='assetpath',
            old_name='aggregate_size',
            new_name='size',
        ),
        migrations.AlterField(
            model_name='assetpath',
            name='asset',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='leaf_paths',
                to='api.asset',
            ),
        ),
        migrations.RemoveConstraint(
            model_name='assetpath',
            name='unique-version-path',
        ),
        migrations.AddConstraint(
            model_name='assetpath',
            constraint=models.UniqueConstraint(
                fields=('version', 'path'),
                include=('size', 'asset'),
                name='unique-version-path',
            ),
        ),
    ]
