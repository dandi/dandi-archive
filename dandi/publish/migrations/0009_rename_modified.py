# Generated by Django 3.0.9 on 2020-08-28 20:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('publish', '0008_draft_version_related_name'),
    ]

    operations = [
        migrations.RenameField(
            model_name='asset',
            old_name='updated',
            new_name='modified',
        ),
        migrations.RenameField(
            model_name='dandiset',
            old_name='updated',
            new_name='modified',
        ),
        migrations.RenameField(
            model_name='draftversion',
            old_name='updated',
            new_name='modified',
        ),
        migrations.RenameField(
            model_name='version',
            old_name='updated',
            new_name='modified',
        ),
    ]
