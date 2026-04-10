from django import forms
from .models import ContactMessage
from apps.base.validation import validate_email_format, validate_nepal_phone_number


class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["full_name", "email", "phone_number", "subject", "message"]
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-gray-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary",
                    "placeholder": "Enter your full name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full rounded-xl border border-gray-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary",
                    "placeholder": "Enter your email",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-gray-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary",
                    "placeholder": "Enter your phone number",
                }
            ),
            "subject": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-gray-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary",
                    "placeholder": "What is this about?",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "w-full rounded-xl border border-gray-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary",
                    "placeholder": "Write your message...",
                    "rows": 5,
                }
            ),
        }

    def clean_phone_number(self):
        return validate_nepal_phone_number(self.cleaned_data.get('phone_number'))
    
    def clean_email(self):
        return validate_email_format(self.cleaned_data.get('email'))
    
        
