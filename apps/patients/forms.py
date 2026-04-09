from datetime import date
import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from apps.patients.models import Patient

User = get_user_model()


def validate_nepal_phone_number(phone_number):
    phone_number = (phone_number or '').strip()

    if not phone_number:
        return phone_number

    phone_number_digits = re.sub(r'[\s\-]', '', phone_number)

    if re.match(r'^(98|97|96)\d{8}$', phone_number_digits):
        return phone_number

    if re.match(r'^\+977\d{9}$', phone_number_digits):
        return phone_number

    if re.match(r'^\+977\d{6,7}$', phone_number_digits):
        return phone_number

    if re.match(r'^0\d{1,2}-\d{5,7}$', phone_number):
        return phone_number

    raise forms.ValidationError(
        'Please enter a valid Nepal phone number. '
        'Formats: 98XXXXXXXX, +9779XXXXXXXX, 061-563200, or +977-1-4123456'
    )


class PatientUserForm(forms.ModelForm):
    """Form for creating Patient User account"""

    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Enter password'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'date_of_birth', 'address']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter username',
                'required': 'required'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter email address',
                'required': 'required'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter first name',
                'required': 'required'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter last name',
                'required': 'required'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter phone number'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter residential address',
                'rows': 3
            }),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if '@' in username:
            raise forms.ValidationError('Username cannot contain @.')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long.')

        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('Password must contain at least one uppercase letter.')

        if not re.search(r'[a-z]', password):
            raise forms.ValidationError('Password must contain at least one lowercase letter.')

        if not re.search(r'\d', password):
            raise forms.ValidationError('Password must contain at least one number.')

        if not re.search(r'[^A-Za-z0-9]', password):
            raise forms.ValidationError('Password must contain at least one special character.')

        user = User(
            username=self.cleaned_data.get('username', ''),
            email=self.cleaned_data.get('email', ''),
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
        )

        try:
            validate_password(password, user=user)
        except forms.ValidationError as error:
            raise forms.ValidationError(error.messages)

        return password


    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth and date_of_birth > date.today():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return date_of_birth

    def clean_phone_number(self):
        return validate_nepal_phone_number(self.cleaned_data.get('phone_number'))
        



class PatientCreateProfileForm(forms.ModelForm):
    """Form for creating patient profile"""

    class Meta:
        model = Patient
        fields = [
            'date_of_birth',
            'gender',
            'blood_group',
            'contact_number',
            'emergency_contact',
            'emergency_contact_name',
            'address',
            'city',
            'state',
            'country',
            'postal_code',
            'medical_history',
            'insurance_provider',
            'insurance_policy_number',
            'profile_picture',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'type': 'date',
                'required': 'required'
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition'
            }),
            'blood_group': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition'
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter contact number',
                'required': 'required'
            }),
            'emergency_contact': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Emergency contact number'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Emergency contact person name'
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Residential address',
                'rows': 3,
                'required': 'required'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'City',
                'required': 'required'
            }),
            'state': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'State/Province',
                'required': 'required'
            }),
            'country': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Country'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Postal/ZIP code'
            }),
            'medical_history': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Medical history and allergies',
                'rows': 4
            }),
            'insurance_provider': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Insurance provider'
            }),
            'insurance_policy_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Policy number'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'accept': 'image/*'
            }),
        }

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth and date_of_birth > date.today():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return date_of_birth

    def clean_contact_number(self):
        return validate_nepal_phone_number(self.cleaned_data.get('contact_number'))

    def clean_emergency_contact(self):
        return validate_nepal_phone_number(self.cleaned_data.get('emergency_contact'))


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

    def clean_contact_number(self):
        return validate_nepal_phone_number(self.cleaned_data.get('contact_number'))

    def clean_emergency_contact(self):
        return validate_nepal_phone_number(self.cleaned_data.get('emergency_contact'))
    
    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth and date_of_birth > date.today():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return date_of_birth


class PatientAccountForm(forms.ModelForm):
    """Form for patients to update username and email."""

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter username',
                'autocomplete': 'username',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter email address',
                'autocomplete': 'email',
            }),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if '@' in username:
            raise forms.ValidationError('Username cannot contain @.')

        user_id = self.instance.id if self.instance and self.instance.id else None
        if User.objects.filter(username=username).exclude(id=user_id).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        user_id = self.instance.id if self.instance and self.instance.id else None
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            raise forms.ValidationError('This email is already registered.')
        return email


