from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class PatientOnlySocialAccountAdapter(DefaultSocialAccountAdapter):
    """Allow Google social login only for patient accounts."""

    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        # When email-auth matches an existing account, enforce patient-only login.
        if getattr(user, "pk", None) and not user.is_patient:
            messages.error(
                request,
                "Unauthorized: Google login is available for patients only.",
            )
            raise ImmediateHttpResponse(redirect("users:login"))

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        User = get_user_model()

        if not user.username:
            base_username = (user.email.split("@")[0] if user.email else "patientuser").lower()
            base_username = "".join(ch for ch in base_username if ch.isalnum() or ch == "_") or "patientuser"
            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exists():
                suffix += 1
                username = f"{base_username}{suffix}"
            user.username = username

        user.user_type = User.UserType.PATIENT
        user.is_default_password = False
        return user
