from django import forms
from django.contrib.auth import get_user_model
from datetime import date
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


class DoctorPasswordChangeForm(forms.Form):
    """Form for changing doctor password during profile update"""
    
    old_password = forms.CharField(
        label='Current Password',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Enter current password',
            'autocomplete': 'current-password'
        })
    )
    
    new_password = forms.CharField(
        label='New Password',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password'
        })
    )
    
    confirm_password = forms.CharField(
        label='Confirm Password',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
    
    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get('old_password', '')
        new_password = cleaned_data.get('new_password', '')
        confirm_password = cleaned_data.get('confirm_password', '')
        
        # If any password field is provided, all must be provided
        if old_password or new_password or confirm_password:
            if not old_password:
                self.add_error('old_password', 'Current password is required to change password.')
            if not new_password:
                self.add_error('new_password', 'New password is required.')
            if not confirm_password:
                self.add_error('confirm_password', 'Password confirmation is required.')
            
            # Verify old password
            if old_password and not self.user.check_password(old_password):
                self.add_error('old_password', 'Current password is incorrect.')
            
            # Check new password length
            if new_password and len(new_password) < 8:
                self.add_error('new_password', 'New password must be at least 8 characters long.')
            
            # Check passwords match
            if new_password and confirm_password and new_password != confirm_password:
                self.add_error('confirm_password', 'Passwords do not match.')
        
        return cleaned_data
