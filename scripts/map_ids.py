"""
Maps the identifiers of all Dandisets to the identifier listed in their metadata.

Run me:
python manage.py runscript map_ids

Identifier cycles are not addressed.
If you have Dandiset 000001 with {"identifier":000002} and Dandiset 000002
with {"identifier":000001}, manual intervention is required.
"""

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.dandiset_migration import move_if_necessary


def run():
    for dandiset in Dandiset.objects.all():
        logs = move_if_necessary(dandiset)
        for line in logs:
            print(line)
