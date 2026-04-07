import re

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

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
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if '@' in username:
            raise forms.ValidationError("Username cannot contain @.")
        return username
    
    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth and date_of_birth > forms.fields.datetime.date.today():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return date_of_birth

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
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.user_type = User.UserType.PATIENT
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
            'placeholder': '+1 (555) 123-4567'
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
        email = self.cleaned_data.get('email')
        user_id = self.instance.id if self.instance and self.instance.id else None
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            raise forms.ValidationError("This email is already in use.")
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and '@' in username:
            raise forms.ValidationError("Username cannot contain @.")
        user_id = self.instance.id if self.instance and self.instance.id else None
        if User.objects.filter(username=username).exclude(id=user_id).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth and date_of_birth > forms.fields.datetime.date.today():
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

        if new_password and not re.search(r'[A-Z]', new_password):
            self.add_error('new_password', 'Password must contain at least one uppercase letter.')

        if new_password and not re.search(r'[a-z]', new_password):
            self.add_error('new_password', 'Password must contain at least one lowercase letter.')

        if new_password and not re.search(r'\d', new_password):
            self.add_error('new_password', 'Password must contain at least one number.')

        if new_password and not re.search(r'[^A-Za-z0-9]', new_password):
            self.add_error('new_password', 'Password must contain at least one special character.')

        if new_password and not self.errors.get('new_password'):
            try:
                validate_password(new_password, user=self.user)
            except forms.ValidationError as error:
                for message in error.messages:
                    self.add_error('new_password', message)

        return cleaned_data