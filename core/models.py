from django.db import models
import uuid

# ----------------------
# Abstract Base Models
# ----------------------

class TimeStampedModel(models.Model):
    """
    Abstract base class that provides created_at and updated_at fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    Abstract base class that uses UUID as the primary key.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Abstract base class that allows soft deletes instead of hard deletes.
    """
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

  