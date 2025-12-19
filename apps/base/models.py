from django.db import models
from model_utils.models import TimeStampedModel, SoftDeletableModel

class BaseModel(TimeStampedModel, SoftDeletableModel):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
