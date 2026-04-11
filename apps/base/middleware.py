from django.shortcuts import redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied

from apps.hospitals.models import HospitalAdmin, HospitalStaff


class AdminHospitalContextMiddleware:
    """Attach hospital scope to request for hospital-bound roles.

    Super admins keep unrestricted access.
    Admin, staff, lab assistant, and pharmacist users are scoped to one hospital.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _resolve_hospital_scope_id(self, user):
        """Return hospital id for hospital-bound roles, otherwise None."""
        if user.is_super_admin:
            return None

        try:
            if user.is_admin:
                return user.hospital_admin_profile.hospital_id

            if user.is_staff_member or user.is_lab_assistant or user.is_pharmacist:
                return user.hospital_staff_profile.hospital_id
        except (HospitalAdmin.DoesNotExist, HospitalStaff.DoesNotExist):
            return None

        return None

    def __call__(self, request):
        # Backward compatibility: many existing views still read admin_hospital_id.
        request.admin_hospital_id = None
        request.hospital_scope_id = None

        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            hospital_scope_id = self._resolve_hospital_scope_id(user)
            request.hospital_scope_id = hospital_scope_id
            request.admin_hospital_id = hospital_scope_id

            if (
                not user.is_super_admin
                and (
                    user.is_admin
                    or user.is_staff_member
                    or user.is_lab_assistant
                    or user.is_pharmacist
                )
                and not hospital_scope_id
            ):
                raise PermissionDenied("Hospital profile is required for this account.")

        return self.get_response(request)


class AdminKhaltiSetupRequiredMiddleware:
    """Force admin users to complete Khalti setup before accessing other pages."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if user and user.is_authenticated and user.is_admin:
            setup_path = reverse('hospitals:khalti_setup')
            exempt_paths = {
                setup_path,
                reverse('users:administer_logout'),
                reverse('users:password_change'),
            }

            current_path = request.path
            if (
                current_path not in exempt_paths
                and not current_path.startswith('/admin/')
            ):
                try:
                    hospital = user.hospital_admin_profile.hospital
                except Exception:
                    hospital = None

                if hospital and (
                    not hospital.khalti_secret_key or not hospital.khalti_public_key
                ):
                    next_url = request.get_full_path()
                    return redirect(f"{setup_path}?next={next_url}")

        return self.get_response(request)