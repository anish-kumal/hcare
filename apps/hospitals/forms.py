from django import forms
from .models import Hospital, HospitalAdmin, HospitalDepartment
from apps.users.models import User


class HospitalForm(forms.ModelForm):
    """Form for creating and updating hospital information"""
    
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
            'is_verified': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-primary bg-gray-100 border border-gray-300 rounded cursor-pointer'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-primary bg-gray-100 border border-gray-300 rounded cursor-pointer'
            }),
        }


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
        username = self.cleaned_data['username']
        if '@' in username:
            raise forms.ValidationError('Username cannot contain @.')
        qs = User.objects.filter(username__iexact=username)
        if self._linked_user:
            qs = qs.exclude(pk=self._linked_user.pk)
        if qs.exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        qs = User.objects.filter(email__iexact=email)
        if self._linked_user:
            qs = qs.exclude(pk=self._linked_user.pk)
        if qs.exists():
            raise forms.ValidationError('This email is already in use.')
        return email

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