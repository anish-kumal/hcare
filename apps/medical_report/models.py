from django.db import models
from django.conf import settings
from apps import hospitals
from apps.base.models import BaseModel

# Create your models here.
class MedicalReport(BaseModel):
    """
    Model to store medical reports for patients
    """
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='medical_reports',
        help_text="Patient associated with this medical report"
    )

    primary_hospital = models.OneToOneField(
        hospitals.models.Hospital,
        on_delete=models.PROTECT,
        related_name='medical_report',
        help_text="Hospital associated with this medical report"
    )

    report_name = models.CharField(
        max_length=200,
        help_text="Name/title of the medical report"
    )

    report_file = models.FileField(
        upload_to='medical_reports/',
        help_text='Uploaded medical report file'
    )

    description = models.TextField(
        blank=True,
        help_text="Description of the medical report"
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='uploaded_medical_reports',
        help_text="User who uploaded the medical report"
    )

    shared_with = models.ManyToManyField(
        hospitals.models.Hospital,
        blank=True,
        related_name='shared_medical_reports',
        help_text="Hospitals this medical report is shared with"
    )

    class Meta:
        verbose_name = 'Medical Report'
        verbose_name_plural = 'Medical Reports' 
        ordering = ['-created']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['primary_hospital']),
            models.Index(fields=['uploaded_by']),
        ]

    def __str__(self):
        return f"Medical Report for {self.patient} at {self.primary_hospital}"

    def get_report_file_url(self):
        """Return a direct URL for opening the report file."""
        if not self.report_file:
            return ''
        return getattr(self.report_file, 'url', '')

    def get_report_download_url(self):
        """Return a URL used by app-level download endpoints."""
        if not self.report_file:
            return ''
        return self.get_report_file_url()
    



