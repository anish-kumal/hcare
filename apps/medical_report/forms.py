from django import forms
from .models import MedicalReport




class AdminMedicalReportForm(forms.ModelForm):
    """
    Admin form for managing medical reports with additional fields
    """
    
    class Meta:
        model = MedicalReport
        fields = ['patient', 'primary_hospital', 'report_name', 'report_file', 'description', 'shared_with', 'uploaded_by']
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
            'uploaded_by': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition'

            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['uploaded_by'].help_text = 'User who uploaded this report'
