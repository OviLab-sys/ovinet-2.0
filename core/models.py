from django.db import models
from .mixins import UUIDModel, TimeStampedModel, SoftDeleteModel
from .managers import SoftDeleteManager, AllObjectsManager

# Attach managers to SoftDeleteModel via a small BaseModel
class BaseModel(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """Common base model: UUID PK, timestamps, and soft delete support."""

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True