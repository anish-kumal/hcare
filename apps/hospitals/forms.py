from django import forms
from .models import Hospital, HospitalAdmin, HospitalDepartment
from .crypto import encrypt_khalti_key
from apps.base.validation import (
    validate_email_format,
    validate_image_max_size,
    validate_strong_password,
    validate_unique_email,
    validate_unique_username,
    validate_username_format,
    validate_nepal_phone_number,
    validate_unique_registration_number,
)
from apps.users.models import User


class HospitalForm(forms.ModelForm):
    """Form for creating and updating hospital information"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['khalti_secret_key'].help_text = 'Leave blank to keep the existing secret key.'
            self.fields['khalti_public_key'].help_text = 'Leave blank to keep the existing public key.'
    
    class Meta:
        model = Hospital
        fields = [
            'name',
            'registration_number',
            'email',
            'phone_number',
            'address',
            'city',
            'state',
            'country',
            'postal_code',
            'description',
            'logo',
            'website',
            'established_date',
            'total_beds',
            'emergency_contact',
            'khalti_secret_key',
            'khalti_public_key',
            'is_verified',
            'is_active',
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter hospital name',
                'required': 'required'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter registration number',
                'required': 'required'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter hospital email',
                'required': 'required'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter phone number',
                'required': 'required'
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter hospital address',
                'rows': 3,
                'required': 'required'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter city',
                'required': 'required'
            }),
            'state': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter state/province',
                'required': 'required'
            }),
            'country': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter country',
                'value': 'Nepal'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter postal code'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter hospital description and facilities',
                'rows': 4
            }),
            'logo': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'accept': 'image/*'
            }),
            'website': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'https://example.com'
            }),
            'established_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'type': 'date'
            }),
            'total_beds': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter total beds',
                'min': '0'
            }),
            'emergency_contact': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter emergency contact number'
            }),
            'khalti_secret_key': forms.PasswordInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter Khalti secret key'
            }, render_value=False),
            'khalti_public_key': forms.PasswordInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter Khalti public key'
            }, render_value=False),
            'is_verified': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-primary bg-gray-100 border border-gray-300 rounded cursor-pointer'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-primary bg-gray-100 border border-gray-300 rounded cursor-pointer'
            }),
        }

    def clean_khalti_secret_key(self):
        secret_key = self.cleaned_data.get('khalti_secret_key')
        if not secret_key and self.instance and self.instance.pk:
            return self.instance.khalti_secret_key
        return secret_key

    def clean_khalti_public_key(self):
        public_key = self.cleaned_data.get('khalti_public_key')
        if not public_key and self.instance and self.instance.pk:
            return self.instance.khalti_public_key
        return public_key

    def clean_logo(self):
        return validate_image_max_size(self.cleaned_data.get('logo'))

    def clean_phone_number(self):
        return validate_nepal_phone_number(self.cleaned_data.get('phone_number'))

    def clean_emergency_contact(self):
        return validate_nepal_phone_number(self.cleaned_data.get('emergency_contact'))

    def clean_registration_number(self):
        exclude_pk = self.instance.pk if self.instance and self.instance.pk else None
        return validate_unique_registration_number(
            self.cleaned_data.get('registration_number'),
            model=Hospital,
            exclude_pk=exclude_pk,
            case_insensitive=True,
            error_message='This registration number is already registered.',
        )

    def clean_email(self):
        email = validate_email_format(self.cleaned_data.get('email'))
        exclude_pk = self.instance.pk if self.instance and self.instance.pk else None
        return validate_unique_email(
            email,
            model=Hospital,
            exclude_pk=exclude_pk,
            case_insensitive=True,
            error_message='This email is already registered.',
        )

    def save(self, commit=True):
        hospital = super().save(commit=False)
        hospital.khalti_secret_key = encrypt_khalti_key(self.cleaned_data.get('khalti_secret_key'))
        hospital.khalti_public_key = encrypt_khalti_key(self.cleaned_data.get('khalti_public_key'))

        if commit:
            hospital.save()
            self.save_m2m()
        return hospital


class HospitalAdminForm(forms.ModelForm):
    """Form for adding/editing hospital admins"""

    username = forms.CharField(
        max_length=150,
        label="Username",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            'placeholder': 'Enter username',
            'required': 'required',
        }),
    )

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            'placeholder': 'Enter email address',
            'required': 'required',
        }),
    )

    first_name = forms.CharField(
        max_length=150,
        required=False,
        label="First Name",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            'placeholder': 'Enter first name',
        }),
    )

    last_name = forms.CharField(
        max_length=150,
        required=False,
        label="Last Name",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            'placeholder': 'Enter last name',
        }),
    )

    phone_number = forms.CharField(
        max_length=15,
        required=False,
        label="Phone Number",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            'placeholder': 'Enter phone number',
        }),
    )

    password = forms.CharField(
        required=False,
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            'placeholder': 'Set a password',
            'autocomplete': 'new-password',
        }),
        help_text='Required when creating a new hospital admin.',
    )
    
    class Meta:
        model = HospitalAdmin
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._linked_user = getattr(self.instance, 'user', None) if self.instance.pk else None

        if self._linked_user:
            self.fields['username'].initial = self._linked_user.username
            self.fields['email'].initial = self._linked_user.email
            self.fields['first_name'].initial = self._linked_user.first_name
            self.fields['last_name'].initial = self._linked_user.last_name
            self.fields['phone_number'].initial = self._linked_user.phone_number
            self.fields['password'].help_text = 'Leave blank to keep the current password.'
        else:
            self.fields['password'].required = True

    def clean_username(self):
        username = validate_username_format(self.cleaned_data.get('username'))
        exclude_pk = self._linked_user.pk if self._linked_user else None
        return validate_unique_username(
            username,
            model=User,
            exclude_pk=exclude_pk,
            case_insensitive=True,
        )

    def clean_email(self):
        email = validate_email_format(self.cleaned_data.get('email'))
        exclude_pk = self._linked_user.pk if self._linked_user else None
        return validate_unique_email(
            email,
            model=User,
            exclude_pk=exclude_pk,
            case_insensitive=True,
            error_message='This email is already in use.',
        )

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if not password:
            return password

        user = self._linked_user or User(
            username=self.cleaned_data.get('username', ''),
            email=self.cleaned_data.get('email', ''),
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
        )

        return validate_strong_password(password, user=user)

    def save(self, commit=True):
        hospital_admin = super().save(commit=False)
        user = self._linked_user or User()

        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone_number = self.cleaned_data['phone_number']
        user.user_type = User.UserType.ADMIN

        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)

        if commit:
            user.save()
            hospital_admin, _ = HospitalAdmin.objects.update_or_create(
                user=user,
                defaults={
                    'hospital': hospital_admin.hospital,
                    'is_active': hospital_admin.is_active,
                },
            )
        else:
            hospital_admin.user = user

        return hospital_admin

class HospitalDepartmentForm(forms.ModelForm):
    """Form for adding/editing hospital departments"""

    class Meta:
        model = HospitalDepartment
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter department name',
                'required': 'required',
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter department code',
                'required': 'required',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter department description',
                'rows': 4,
            }),
        }

class HospitalRegistrationForm(forms.ModelForm):
    """Form for hospital registration by new hospitals"""

    class Meta:
        model = Hospital
        fields = [
            'name',
            'registration_number',
            'email',
            'phone_number',
            'address',
            'city',
            'state',
            'country',
            'postal_code',
            'description',
            'logo',
            'website',
            'established_date',
            'total_beds',
            'emergency_contact',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter hospital name',
                'required': 'required'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter registration number',
                'required': 'required'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter hospital email',
                'required': 'required'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter phone number',
                'required': 'required'
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter hospital address',
                'rows': 3,
                'required': 'required'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter city',
                'required': 'required'
            }),
            'state': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter state/province',
                'required': 'required'
            }),
            'country': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter country',
                'value': 'Nepal'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter postal code'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter hospital description and facilities',
                'rows': 4
            }),
            'logo': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'accept': 'image/*'
            }),
            'website': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'https://example.com'
            }),
            'established_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'type': 'date'
            }),
            'total_beds': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter total beds',
                'min': '0'
            }),
            'emergency_contact': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Enter emergency contact number'
            }),
        }

    def clean_logo(self):
        return validate_image_max_size(self.cleaned_data.get('logo'))

    def clean_phone_number(self):
        return validate_nepal_phone_number(self.cleaned_data.get('phone_number'))

    def clean_emergency_contact(self):
        return validate_nepal_phone_number(self.cleaned_data.get('emergency_contact'))
        
    def clean_registration_number(self):
        exclude_pk = self.instance.pk if self.instance and self.instance.pk else None
        return validate_unique_registration_number(
            self.cleaned_data.get('registration_number'),
            model=Hospital,
            exclude_pk=exclude_pk,
            case_insensitive=True,
            error_message='This registration number is already registered.',
        )

    def clean_email(self):
        email = validate_email_format(self.cleaned_data.get('email'))
        exclude_pk = self.instance.pk if self.instance and self.instance.pk else None
        return validate_unique_email(
            email,
            model=Hospital,
            exclude_pk=exclude_pk,
            case_insensitive=True,
            error_message='This email is already registered.',
        )

class KhaltiSetupForm(forms.ModelForm):
    """Form for setting up Khalti payment keys - Only khalti_secret_key and khalti_public_key"""
    
    khalti_secret_key = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            'placeholder': 'Enter Khalti Secret Key',
            'required': 'required',
        }),
        label='Khalti Secret Key'
    )
    
    khalti_public_key = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            'placeholder': 'Enter Khalti Public Key',
            'required': 'required',
        }),
        label='Khalti Public Key'
    )
    
    class Meta:
        model = Hospital
        fields = ['khalti_secret_key', 'khalti_public_key']
    
    def clean(self):
        cleaned_data = super().clean()
        secret_key = cleaned_data.get('khalti_secret_key')
        public_key = cleaned_data.get('khalti_public_key')
        
        if not secret_key or not public_key:
            raise forms.ValidationError('Both Khalti keys are required.')
        
        return cleaned_data

    def save(self, commit=True):
        hospital = super().save(commit=False)
        hospital.khalti_secret_key = encrypt_khalti_key(self.cleaned_data['khalti_secret_key'])
        hospital.khalti_public_key = encrypt_khalti_key(self.cleaned_data['khalti_public_key'])

        if commit:
            hospital.save()
            self.save_m2m()
        return hospital