from django.db import models
from model_utils.models import TimeStampedModel

class BaseModel(TimeStampedModel):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
