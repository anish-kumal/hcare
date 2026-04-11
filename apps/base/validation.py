import re
from datetime import date
from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email as django_validate_email
from django.contrib.auth.password_validation import validate_password


DEFAULT_MAX_IMAGE_UPLOAD_SIZE_MB = 5


def validate_username_format(username):
    username = (username or '').strip()
    if '@' in username:
        raise forms.ValidationError('Username cannot contain @.')
    return username


def validate_email_format(email):
    email = (email or '').strip()
    if not email:
        return email

    try:
        django_validate_email(email)
    except DjangoValidationError:
        raise forms.ValidationError('Please enter a valid email address.')

    return email


def _validate_unique_value(
    value,
    *,
    model,
    field_name,
    exclude_pk=None,
    case_insensitive=False,
    error_message='This value already exists.',
):
    if not value:
        return value

    lookup = f'{field_name}__iexact' if case_insensitive else field_name
    queryset = model.objects.filter(**{lookup: value})

    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)

    if queryset.exists():
        raise forms.ValidationError(error_message)

    return value


def validate_unique_username(
    username,
    *,
    model,
    exclude_pk=None,
    case_insensitive=False,
    error_message='Invalid username.',
):
    return _validate_unique_value(
        username,
        model=model,
        field_name='username',
        exclude_pk=exclude_pk,
        case_insensitive=case_insensitive,
        error_message=error_message,
    )


def validate_unique_email(
    email,
    *,
    model,
    exclude_pk=None,
    case_insensitive=False,
    error_message='This email is already registered.',
):
    return _validate_unique_value(
        email,
        model=model,
        field_name='email',
        exclude_pk=exclude_pk,
        case_insensitive=case_insensitive,
        error_message=error_message,
    )


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


def validate_date_not_in_future(value, field_label='Date'):
    if value and value > date.today():
        raise forms.ValidationError(f'{field_label} cannot be in the future.')
    return value


def validate_image_max_size(uploaded_file, max_size_mb=DEFAULT_MAX_IMAGE_UPLOAD_SIZE_MB):
    if not uploaded_file:
        return uploaded_file

    max_size_bytes = max_size_mb * 1024 * 1024

    file_size = getattr(uploaded_file, 'size', None)
    if file_size is None:
        nested_file = getattr(uploaded_file, 'file', None)
        file_size = getattr(nested_file, 'size', None)

    # Some storage-backed resources (e.g. existing Cloudinary values on edit)
    # don't expose a local size attribute. In that case, skip size validation.
    if file_size is None:
        return uploaded_file

    if file_size > max_size_bytes:
        raise forms.ValidationError(
            f'Image size must be {max_size_mb}MB or less.'
        )

    return uploaded_file


def validate_strong_password(password, user=None):
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

    try:
        validate_password(password, user=user)
    except forms.ValidationError as error:
        raise forms.ValidationError(error.messages)

    return password
