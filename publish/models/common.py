from django.db import models


class SelectRelatedManager(models.Manager):
    def __init__(self, *related_fields):
        self.related_fields = related_fields
        super().__init__()

    def get_queryset(self):
        return super().get_queryset().select_related(*self.related_fields)
