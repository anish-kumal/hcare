from django.contrib.auth import get_user_model
from django.conf import settings


def get_axes_username(request, credentials=None):
    """Normalize login identifiers so Axes tracks account lock by canonical username."""
    username_field = getattr(settings, 'AXES_USERNAME_FORM_FIELD', 'username')

    identifier = None
    if credentials:
        identifier = credentials.get(username_field)

    if not identifier:
        request_data = getattr(request, 'data', request.POST)
        identifier = request_data.get(username_field)

    if not identifier:
        return ''

    identifier = str(identifier).strip()
    if not identifier:
        return ''

    user_model = get_user_model()

    try:
        if '@' in identifier:
            user = user_model.objects.only('username').get(email__iexact=identifier)
            return user.username.lower()

        user = user_model.objects.only('username').get(username__iexact=identifier)
        return user.username.lower()
    except user_model.DoesNotExist:
        # Fall back to normalized raw identifier so unknown users are still rate-limited.
        return identifier.lower()
