from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameModelBackend(ModelBackend):
    """Authenticate users with either username or email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        # AuthenticationForm passes the identifier as "username" by default.
        identifier = username or kwargs.get("email") or kwargs.get("username")
        if identifier is None or password is None:
            return None

        user_model = get_user_model()

        try:
            if "@" in identifier:
                user = user_model.objects.get(email__iexact=identifier)
            else:
                user = user_model.objects.get(username=identifier)
        except user_model.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None