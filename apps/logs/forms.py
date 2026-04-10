from django import forms
from .models import LogEntry


class LogEntryForm(forms.ModelForm):
    """Form for creating and updating log entries"""
    
    class Meta:
        model = LogEntry
        fields = ['user', 'action', 'details']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'Select User'
            }),
            'action': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter action description'
            }),
            'details': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter additional details',
                'rows': 5
            }),
        }
        labels = {
            'user': 'User',
            'action': 'Action',
            'details': 'Details',
        }
