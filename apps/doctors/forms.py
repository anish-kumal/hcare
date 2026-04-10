from django import forms
from django.contrib.auth import get_user_model
from datetime import date
from .models import Doctor, DoctorSchedule
from apps.base.validation import (
    validate_date_not_in_future,
    validate_email_format,
    validate_image_max_size,
    validate_nepal_phone_number,
    validate_strong_password,
    validate_unique_email,
    validate_unique_username,
    validate_username_format,
)

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
        username = validate_username_format(self.cleaned_data.get('username'))
        exclude_pk = self.instance.pk if self.instance and self.instance.pk else None
        return validate_unique_username(username, model=User, exclude_pk=exclude_pk)
    
    def clean_email(self):
        email = validate_email_format(self.cleaned_data.get('email'))
        exclude_pk = self.instance.pk if self.instance and self.instance.pk else None
        return validate_unique_email(email, model=User, exclude_pk=exclude_pk)

    def clean_date_of_birth(self):
        return validate_date_not_in_future(
            self.cleaned_data.get('date_of_birth'),
            field_label='Date of birth'
        )

    def clean_phone_number(self):
        return validate_nepal_phone_number(self.cleaned_data.get('phone_number'))
        
    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        user = User(
            username=self.cleaned_data.get('username', ''),
            email=self.cleaned_data.get('email', ''),
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
        )

        return validate_strong_password(password, user=user)



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

    def clean_password(self):
        password = self.cleaned_data.get('password', '')

        # Password update is optional. If provided, enforce strong password rules.
        if not password:
            return password

        user = User(
            username=self.cleaned_data.get('username', ''),
            email=self.cleaned_data.get('email', ''),
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
        )

        return validate_strong_password(password, user=user)

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

    def clean_profile_picture(self):
        return validate_image_max_size(self.cleaned_data.get('profile_picture'))


class DoctorScheduleForm(forms.ModelForm):
    """Form for creating/editing doctor schedule"""

    def __init__(self, *args, **kwargs):
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
        if not self.doctor and self.instance and self.instance.pk:
            self.doctor = self.instance.doctor

    
    
    class Meta:
        model = DoctorSchedule
        fields = ['weekday', 'start_time', 'end_time', 'slot_duration', 'max_patients', 'is_available']
        widgets = {
            'weekday': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition'
            }),
            'start_time': forms.TimeInput(format='%H:%M', attrs={
                'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
                'type': 'time'
            }),
            'end_time': forms.TimeInput(format='%H:%M', attrs={
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

    def clean(self):
        cleaned_data = super().clean()
        weekday = cleaned_data.get('weekday')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        slot_duration = cleaned_data.get('slot_duration')

        if not start_time or not end_time:
            return cleaned_data

        start_minutes = (start_time.hour * 60) + start_time.minute
        end_minutes = (end_time.hour * 60) + end_time.minute
        duration_minutes = end_minutes - start_minutes

        if duration_minutes == 0:
            self.add_error('end_time', 'Start time and end time cannot be the same.')
            return cleaned_data

        if duration_minutes < 0:
            self.add_error('end_time', 'End time must be after start time.')
            return cleaned_data

        if duration_minutes > 240:
            self.add_error('end_time', 'Schedule duration cannot be more than 4 hours.')

        if slot_duration:
            slot_count = duration_minutes / slot_duration
            if slot_duration > duration_minutes:
                self.add_error('slot_duration', 'Slot duration cannot be greater than the total schedule duration.')
            elif slot_count <= 1 :
                self.add_error('slot_duration', 'Schedule must contain at least one slot.')

        if self.doctor and weekday is not None:
            conflicting_schedules = DoctorSchedule.objects.filter(
                doctor=self.doctor,
                weekday=weekday,
                start_time__lt=end_time,
                end_time__gt=start_time,
            )

            if self.instance and self.instance.pk:
                conflicting_schedules = conflicting_schedules.exclude(pk=self.instance.pk)

            if conflicting_schedules.exists():
                self.add_error('start_time', 'This time range overlaps with another schedule for the same day.')
                self.add_error('end_time', 'Please choose a non-overlapping end time.')

        return cleaned_data


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
