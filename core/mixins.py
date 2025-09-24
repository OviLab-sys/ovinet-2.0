import uuid
from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)


    class Meta:
        abstract = True




class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        abstract = True




class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)


    objects = None # default manager will be set in managers.py
    all_objects = None


    class Meta:
        abstract = True


    def delete(self, using=None, keep_parents=False):
        """Soft delete: mark as deleted instead of removing from DB."""
        self.is_deleted = True
        self.save(update_fields=["is_deleted"])


    def restore(self):
        self.is_deleted = False
        self.save(update_fields=["is_deleted"])
        
    def hard_delete(self, using=None, keep_parents=False):
        """
        Optional: provide a true delete if you ever need to remove permanently.
        """
        super().delete(using=using, keep_parents=keep_parents)
