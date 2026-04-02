from django import forms
from django.contrib.auth import get_user_model
from datetime import date
import re
from .models import Doctor, DoctorSchedule

User = get_user_model()


class DoctorUserForm(forms.ModelForm):
    """Form for creating Doctor User account"""
    
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
            raise forms.ValidationError("Username cannot contain @.")
        queryset = User.objects.filter(username=username)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("This username is already taken.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        queryset = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth and date_of_birth > date.today():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return date_of_birth

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
        



class DoctorUserUpdateForm(DoctorUserForm):
    """Form for updating Doctor User account"""

    password = forms.CharField(
        label='New Password',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Leave blank to keep current password'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password') or ''

        if password and len(password) < 8:
            self.add_error('password', 'Password must be at least 8 characters long.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('password')

        if new_password:
            user.set_password(new_password)
            user.is_default_password = False

        if commit:
            user.save()

        return user

    class Meta(DoctorUserForm.Meta):
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'date_of_birth', 'address']
    



class DoctorProfileForm(forms.ModelForm):
    """Form for creating Doctor profile"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.initial.get('joining_date'):
            self.initial['joining_date'] = date.today()
    
    class Meta:
        model = Doctor
        fields = ['department', 'specialization', 'license_number', 'employee_id', 
                  'qualification', 'experience_years', 'bio', 'consultation_fee', 
                  'profile_picture', 'is_available', 'joining_date']
        widgets = {
            'department': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition'
            }),
            'specialization': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'E.g., Cardiology, Pediatrics, General Practice',
                'required': 'required'
            }),
            'license_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter medical license number',
                'required': 'required'
            }),
            'employee_id': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter employee ID',
                'required': 'required'
            }),
            'qualification': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'E.g., MBBS, MD, MS',
                'required': 'required'
            }),
            'experience_years': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Years of experience',
                'min': 0,
                'required': 'required'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Enter doctor biography',
                'rows': 4
            }),
            'consultation_fee': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'placeholder': 'Consultation fee',
                'min': 0,
                'step': 0.01
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'accept': 'image/*'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-primary bg-gray-100 border border-gray-300 rounded cursor-pointer'
            }),
            'joining_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'type': 'date'
            }),
        }
    
    def clean_license_number(self):
        license_number = self.cleaned_data.get('license_number')
        queryset = Doctor.objects.filter(license_number=license_number)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if license_number and queryset.exists():
            raise forms.ValidationError("This license number is already registered.")
        return license_number
    
    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id')
        queryset = Doctor.objects.filter(employee_id=employee_id)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if employee_id and queryset.exists():
            raise forms.ValidationError("This employee ID is already registered.")
        return employee_id

    def clean_experience_years(self):
        experience_years = self.cleaned_data.get('experience_years')
        if experience_years is not None and experience_years > 100:
            raise forms.ValidationError("Experience years cannot be more than 100.")
        return experience_years


class DoctorScheduleForm(forms.ModelForm):
    """Form for creating/editing doctor schedule"""
    
    class Meta:
        model = DoctorSchedule
        fields = ['weekday', 'start_time', 'end_time', 'slot_duration', 'max_patients', 'is_available']
        widgets = {
            'weekday': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'type': 'time'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'type': 'time'
            }),
            'slot_duration': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'min': 1
            }),
            'max_patients': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'min': 1
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-primary bg-gray-100 border border-gray-300 rounded cursor-pointer'
            }),
        }


class DoctorSelfProfileForm(DoctorProfileForm):
    """Doctor self-edit form (consultation fee is read-only for doctors)."""

    class Meta(DoctorProfileForm.Meta):
        fields = [
            'department',
            'specialization',
            'license_number',
            'employee_id',
            'qualification',
            'experience_years',
            'bio',
            'profile_picture',
            'is_available',
            'joining_date',
        ]
