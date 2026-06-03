import uuid
from django.db import models
from .base import SoftDeleteModel

class Category(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.PROTECT, related_name='children'
    )
    slug = models.SlugField(unique=True)
    full_path = models.CharField(max_length=1024)
    level = models.PositiveSmallIntegerField(default=1)

    class Meta:
        indexes = [models.Index(fields=['slug'])]

    def __str__(self):
        return self.name
