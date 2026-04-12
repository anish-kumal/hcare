from django.contrib.auth import get_user_model

User = get_user_model()


def get_axes_username(request, credentials=None):
    identifier = (credentials or {}).get("username")

    if not identifier:
        return None

    try:
        if "@" in identifier:
            user = User.objects.get(email__iexact=identifier)
        else:
            user = User.objects.get(username__iexact=identifier)

        # Return one canonical value so email/username map to the same lock key.
        return user.username

    except User.DoesNotExist:
        return identifier
