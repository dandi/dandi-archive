from __future__ import annotations

import logging
from typing import Optional

from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import models

from publish.girder import GirderClient, GirderError


logger = logging.getLogger(__name__)


class Dandiset(models.Model):
    # Don't add beginning and end markers, so this can be embedded in larger regexes
    IDENTIFIER_REGEX = r'\d{6}'
    GIRDER_ID_REGEX = r'[0-9a-f]{24}'

    draft_folder_id = models.CharField(
        max_length=24, validators=[RegexValidator(f'^{GIRDER_ID_REGEX}$')],
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    @property
    def identifier(self) -> Optional[str]:
        # Compare against None, to allow id 0
        return f'{self.id:06}' if self.id is not None else ''

    def __str__(self) -> str:
        return self.identifier

    @classmethod
    def from_girder(cls, draft_folder_id: str, client: GirderClient):
        """
        Return the Dandiset corresponding to a Girder `draft_folder_id`.

        Creates the Dandiset if it does not exist.
        """
        draft_folder = client.get_json(f'folder/{draft_folder_id}')

        dandiset_identifier = draft_folder['name']
        try:
            dandiset_id = int(dandiset_identifier)
        except ValueError:
            raise GirderError(f'Invalid Dandiset identifier in Girder: {dandiset_identifier}')
        try:
            dandiset = Dandiset.objects.get(id=dandiset_id)
        except ObjectDoesNotExist:
            dandiset = Dandiset(id=dandiset_id, draft_folder_id=draft_folder_id)
            dandiset.save()
        else:
            # If the Dandiset existed, sync the draft_folder_id
            if dandiset.draft_folder_id != draft_folder_id:
                raise GirderError(
                    f'Known Dandiset identifer {dandiset.identifier} does not'
                    f'match existing Girder folder id {dandiset.draft_folder_id}'
                )
        return dandiset
