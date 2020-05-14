from django.db import models
from django.contrib.postgres.fields import JSONField


class Dandiset(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    dandi_id = models.CharField(max_length=16)
    version = models.CharField(max_length=13)
    metadata = JSONField(default=dict)

    class Meta:
        unique_together = [['dandi_id', 'version']]


class NWBFile(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    dandiset = models.ForeignKey(
        Dandiset, related_name='nwb_files', on_delete=models.CASCADE)
    name = models.CharField(max_length=512)
    size = models.BigIntegerField()
    sha256 = models.CharField(max_length=64)
    metadata = JSONField(default=dict)

    file = models.FileField()

    class Meta:
        db_table = 'nwb_file'
