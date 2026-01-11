from django import forms
from apps.patients.models import PatientAppointment


class AppointmentBookingForm(forms.ModelForm):
    """Form for patients to book appointments"""
    
    class Meta:
        model = PatientAppointment
        fields = ['appointment_date', 'appointment_time', 'reason', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True,
            }),
            'appointment_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control',
                'required': True,
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Please describe the reason for your visit',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any additional notes (optional)',
            }),
        }


class AppointmentEditForm(forms.ModelForm):
    """Form for patients to edit their appointments"""
    
    class Meta:
        model = PatientAppointment
        fields = ['appointment_date', 'appointment_time', 'reason', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True,
            }),
            'appointment_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control',
                'required': True,
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Please describe the reason for your visit',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any additional notes (optional)',
            }),
        }
