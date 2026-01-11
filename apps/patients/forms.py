from django import forms
from apps.patients.models import Patient


class PatientProfileForm(forms.ModelForm):
    """Form for patients to edit their profile"""
    
    class Meta:
        model = Patient
        fields = ['date_of_birth', 'gender', 'blood_group', 'contact_number', 
                  'emergency_contact', 'emergency_contact_name', 'address', 'city', 'state', 'country']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            }),
            'blood_group': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Your contact number',
            }),
            'emergency_contact': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Emergency contact number',
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Emergency contact person name',
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'rows': 2,
                'placeholder': 'Your residential address',
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'City',
            }),
            'state': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'State/Province',
            }),
            'country': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Country',
            }),
        }
