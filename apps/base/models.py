from django.db import models
from model_utils.models import TimeStampedModel

class BaseModel(TimeStampedModel):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class ContactMessage(BaseModel):
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    subject = models.CharField(max_length=180)
    message = models.TextField()

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.full_name} - {self.subject}"
