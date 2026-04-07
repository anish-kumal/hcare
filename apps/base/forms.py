from django import forms
from .models import ContactMessage
import re


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
        phone_number = self.cleaned_data.get('phone_number', '').strip()
        
        if not phone_number:
            return phone_number
        
        # Remove spaces and hyphens for validation
        phone_number_digits = re.sub(r'[\s\-]', '', phone_number)
        
        # Nepal mobile number: 10 digits starting with 98, 97, 96 (e.g., 9841234567)
        if re.match(r'^(98|97|96)\d{8}$', phone_number_digits):
            return phone_number
        
        # Nepal international format: +977 followed by 9 digits (e.g., +9779841234567)
        if re.match(r'^\+977\d{9}$', phone_number_digits):
            return phone_number
        
        # Nepal landline: +977 with area code (5-7 digits) (e.g., +97714-1234567)
        if re.match(r'^\+977\d{6,7}$', phone_number_digits):
            return phone_number
        
        # Local landline format: area code + hyphen + local number (e.g., 061-563200, 01-4123456)
        if re.match(r'^0\d{1,2}-\d{5,7}$', phone_number):
            return phone_number
        
        raise forms.ValidationError(
            "Please enter a valid Nepal phone number. "
            "Formats: 98XXXXXXXX, +9779XXXXXXXX, 061-563200, or +977-1-4123456"
        )
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            raise forms.ValidationError("Please enter a valid email address.")
        return email
    
        
