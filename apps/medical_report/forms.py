from django import forms
from django.db.models import Q
from apps.patients.models import Patient
from apps.hospitals.models import Hospital
from .models import MedicalReport



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
                'placeholder': 'Enter Report Name',
                'required': True
            }),
            'report_file': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx',
                'required': True
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

            # Set and lock primary_hospital to user's hospital
            self.fields['primary_hospital'].queryset = Hospital.objects.filter(pk=user_hospital.pk)
            self.fields['primary_hospital'].initial = user_hospital
            self.fields['primary_hospital'].widget = forms.HiddenInput()
            self.fields['primary_hospital'].disabled = True
        else:
            # Super admin fallback - all patients and hospitals available
            self.fields['patient'].queryset = Patient.objects.all()

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
