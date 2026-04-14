from django import forms
from django.db.models import Q
from django.core.exceptions import ValidationError
from apps.patients.models import Patient
from apps.hospitals.models import Hospital
from .models import MedicalReport

ALLOWED_EXTENSIONS = ('jpg', 'jpeg', 'png', 'webp')
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_report_image(uploaded_file, field_name):
    """Validate file size and extension for report images."""
    if not uploaded_file:
        return

    if hasattr(uploaded_file, 'size') and uploaded_file.size > MAX_FILE_SIZE:
        raise ValidationError({
            field_name: f'File size must not exceed 10MB. Current size: {uploaded_file.size / (1024*1024):.2f}MB'
        })

    file_ext = uploaded_file.name.split('.')[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValidationError({
            field_name: f'Invalid file format. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
        })


class AdminMedicalReportForm(forms.ModelForm):
    """
    Admin form for managing medical reports with additional fields
    """
    class Meta:
        model = MedicalReport
        fields = ['patient', 'primary_hospital', 'report_name', 'report_file', 'description', 'shared_with']
        widgets = {
            'patient': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Select Patient'
            }),
            'primary_hospital': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Select Hospital'
            }),
            'report_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter Report Name'
            }),
            'report_file': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'accept': '.jpg,.jpeg,.png,.webp'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter Description (Optional)',
                'rows': 3
            }),
            'shared_with': forms.CheckboxSelectMultiple(attrs={
                'class' : 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Select Hospitals to Share With (Optional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Hide uploaded_by field from form; populated automatically from request.user
        if 'uploaded_by' in self.fields:
            self.fields.pop('uploaded_by')

        user_hospital = None
        if self.user:
            if hasattr(self.user, 'hospital_admin_profile'):
                user_hospital = self.user.hospital_admin_profile.hospital
            elif hasattr(self.user, 'doctor_profile'):
                user_hospital = self.user.doctor_profile.hospital
            elif hasattr(self.user, 'hospital_staff_profile'):
                user_hospital = self.user.hospital_staff_profile.hospital

        # Restrict patient choices to hospital patients and hospital appointment patients
        if user_hospital:
            self.fields['patient'].queryset = Patient.objects.filter(
                Q(hospital=user_hospital) | Q(appointments__hospital=user_hospital)
            ).distinct()

            # Do not allow sharing back to the requester's own hospital.
            self.fields['shared_with'].queryset = Hospital.objects.exclude(pk=user_hospital.pk)

            # Set and lock primary_hospital to user's hospital
            self.fields['primary_hospital'].queryset = Hospital.objects.filter(pk=user_hospital.pk)
            self.fields['primary_hospital'].initial = user_hospital
            self.fields['primary_hospital'].widget = forms.HiddenInput()
            self.fields['primary_hospital'].disabled = True
        else:
            # Super admin fallback - all patients and hospitals available
            self.fields['patient'].queryset = Patient.objects.all()
            if self.instance and self.instance.primary_hospital_id:
                self.fields['shared_with'].queryset = Hospital.objects.exclude(
                    pk=self.instance.primary_hospital_id
                )

    def clean(self):
        cleaned_data = super().clean()
        report_file = cleaned_data.get('report_file')
        if not self.instance.pk and not report_file:
            raise ValidationError({'report_file': 'Report image is required.'})
        validate_report_image(report_file, 'report_file')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Save primary_hospital from user context when available
        if self.user and hasattr(self.user, 'hospital_admin_profile'):
            instance.primary_hospital = self.user.hospital_admin_profile.hospital
        elif self.user and hasattr(self.user, 'doctor_profile'):
            instance.primary_hospital = self.user.doctor_profile.hospital
        elif self.user and hasattr(self.user, 'hospital_staff_profile'):
            instance.primary_hospital = self.user.hospital_staff_profile.hospital

        # Always set uploaded_by to logged in user if available
        if self.user:
            instance.uploaded_by = self.user

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class PatientMedicalReportShareForm(forms.ModelForm):
    """Patient form that only allows editing hospital sharing."""

    class Meta:
        model = MedicalReport
        fields = ['shared_with']
        widgets = {
            'shared_with': forms.CheckboxSelectMultiple(attrs={
                'class': 'w-full rounded-lg border border-gray-300 p-3 text-gray-900'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.primary_hospital_id:
            self.fields['shared_with'].queryset = Hospital.objects.exclude(
                pk=self.instance.primary_hospital_id
            )
