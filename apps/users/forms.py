from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from apps.base.validation import (
    validate_date_not_in_future,
    validate_email_format,
    validate_nepal_phone_number,
    validate_strong_password,
    validate_unique_email,
    validate_unique_username,
    validate_username_format,
)

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    """
    Custom registration form for creating new users
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'anish@gmail.com'
        })
    )
    
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Enter your username'
        })
    )
    
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Enter your first name'
        })
    )
    
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Enter your last name'
        })
    )
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Enter your password'
        })
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Confirm your password'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def clean_email(self):
        email = validate_email_format(self.cleaned_data.get('email'))
        return validate_unique_email(email, model=User)

    def clean_username(self):
        return validate_username_format(self.cleaned_data.get('username'))
    
    def clean_date_of_birth(self):
        return validate_date_not_in_future(
            self.cleaned_data.get('date_of_birth'),
            field_label='Date of birth'
        )

    def clean_password1(self):
        password = self.cleaned_data.get('password1', '')
        user = User(
            username=self.cleaned_data.get('username', ''),
            email=self.cleaned_data.get('email', ''),
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
        )

        return validate_strong_password(password, user=user)
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.user_type = User.UserType.PATIENT
        user.is_active = False
        user.is_default_password = False
        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    """
    Custom login form with styled fields
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Enter your email or username'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Enter your password'
        })
    )

class UserManagementForm(forms.ModelForm):
    """
    Form for managing users (Create/Update) by Super Admin and Hospital Admin
    """
    USER_TYPE_CHOICES = [
        (User.UserType.STAFF, 'Staff'),
        (User.UserType.LAB_ASSISTANT, 'Lab Technician'),
        (User.UserType.PHARMACIST, 'Pharmacist'),
    ]


    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Leave blank to keep current password'
        }),
        help_text='Leave blank if not changing password'
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'user@example.com'
        })
    )
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'username'
        })
    )
    
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'First Name'
        })
    )
    
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Last Name'
        })
    )
    
    user_type = forms.ChoiceField(
        choices=USER_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition'
        })
    )
    
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': '+977-98XXXXXXXX'
        })
    )
    
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition'
        })
    )
    
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'User address',
            'rows': 3
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'user_type', 'phone_number', 'date_of_birth', 'address']

    
    def clean_email(self):
        email = validate_email_format(self.cleaned_data.get('email'))
        user_id = self.instance.id if self.instance and self.instance.id else None
        return validate_unique_email(
            email,
            model=User,
            exclude_pk=user_id,
            error_message='This email is already in use.',
        )
    
    def clean_username(self):
        username = validate_username_format(self.cleaned_data.get('username'))
        user_id = self.instance.id if self.instance and self.instance.id else None
        return validate_unique_username(username, model=User, exclude_pk=user_id)

    def clean_date_of_birth(self):
        return validate_date_not_in_future(
            self.cleaned_data.get('date_of_birth'),
            field_label='Date of birth'
        )
    
    def clean_phone_number(self):
        return validate_nepal_phone_number(self.cleaned_data.get('phone_number'))

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if not password:
            # On update, blank means keep the existing password unchanged.
            if self.instance and self.instance.pk:
                return password
            raise forms.ValidationError('Password is required when creating a user.')

        user = User(
            username=self.cleaned_data.get('username', ''),
            email=self.cleaned_data.get('email', ''),
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
        )

        return validate_strong_password(password, user=user)


    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
            user.is_default_password = False
        if commit:
            user.save()
        return user


class PasswordChangeForm(forms.Form):
    """Generic form for changing user password (used by all user types)"""
    
    old_password = forms.CharField(
        label='Current Password',
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Enter current password',
            'autocomplete': 'current-password'
        })
    )
    
    new_password = forms.CharField(
        label='New Password',
        required=True,
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password'
        })
    )
    
    confirm_password = forms.CharField(
        label='Confirm Password',
        required=True,
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
        old_password = cleaned_data.get('old_password')
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if old_password and not self.user.check_password(old_password):
            self.add_error('old_password', 'Current password is incorrect.')

        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')

        if new_password and old_password and new_password == old_password:
            self.add_error('new_password', 'New password must be different from the current password.')

        if new_password and not self.errors.get('new_password'):
            try:
                validate_strong_password(new_password, user=self.user)
            except forms.ValidationError as error:
                for message in error.messages:
                    self.add_error('new_password', message)

        return cleaned_data


class UserSelfProfileForm(forms.ModelForm):
    """Allow logged-in staff users to edit their own basic profile fields."""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'user@example.com'
        })
    )

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'username'
        })
    )

    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'First Name'
        })
    )

    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': 'Last Name'
        })
    )

    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'placeholder': '+977-98XXXXXXXX'
        })
    )

    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition'
        })
    )

    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-300 text-gray-900 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition',
            'rows': 3,
            'placeholder': 'Address'
        })
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'phone_number', 'date_of_birth', 'address'
        ]

    def clean_email(self):
        email = validate_email_format(self.cleaned_data.get('email'))
        return validate_unique_email(email, model=User, exclude_pk=self.instance.pk)

    def clean_username(self):
        username = validate_username_format(self.cleaned_data.get('username'))
        return validate_unique_username(username, model=User, exclude_pk=self.instance.pk)

    def clean_date_of_birth(self):
        return validate_date_not_in_future(
            self.cleaned_data.get('date_of_birth'),
            field_label='Date of birth'
        )

    def clean_phone_number(self):
        return validate_nepal_phone_number(self.cleaned_data.get('phone_number'))