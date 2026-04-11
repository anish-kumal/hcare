from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin:

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        if user.is_super_admin:
            return redirect(reverse_lazy('super_admin_dashboard'))
        elif user.is_admin:
            return redirect(reverse_lazy('admin_dashboard'))
        elif user.is_doctor:
            return redirect(reverse_lazy('doctor_dashboard'))
        elif user.is_lab_assistant:
            return redirect(reverse_lazy('lab_assistant_dashboard'))
        elif user.is_pharmacist:
            return redirect(reverse_lazy('pharmacist_dashboard'))
        elif user.is_patient:
            return redirect(reverse_lazy('patient_dashboard'))

        return super().dispatch(request, *args, **kwargs)
    

class SuperAdminOnlyMixin(LoginRequiredMixin):
    """Mixin to restrict access to super admin users only"""
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_super_admin:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)

class SuperAdminAndAdminOnlyMixin(LoginRequiredMixin):
    """Mixin to restrict access to super admin and admin users only"""
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_super_admin or request.user.is_admin):
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)
    
class AdminOnlyMixin(LoginRequiredMixin):
    """Mixin to restrict access to admin users only"""
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_admin:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)

class SuperAdminAdminStaffOnlyMixin(LoginRequiredMixin):
    """Mixin to restrict access to super admin, admin, and staff users only"""
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_super_admin or request.user.is_admin or request.user.is_staff_member):
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)
    

class AdminStaffOnlyMixin(LoginRequiredMixin):
    """Mixin to restrict access to admin and staff users only"""
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_admin or request.user.is_staff_member):
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)
    

class AdminLabAssistantOnlyMixin(LoginRequiredMixin):
    """Mixin to restrict access to admin and lab assistant users only"""
    login_url = 'users:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_admin or request.user.is_lab_assistant):
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)

class AdminPharmacistOnlyMixin(LoginRequiredMixin):
    """Mixin to restrict access to admin and pharmacist users only"""
    login_url = 'users:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_admin or request.user.is_pharmacist):
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)

class AdminHospitalScopedQuerysetMixin:
    """Scope querysets by hospital for hospital-bound users.

    Super admin keeps full access.
    Admin, staff, lab assistant, and pharmacist are scoped to one hospital.
    """

    def _is_hospital_scoped_user(self):
        user = self.request.user
        return (
            user.is_admin
            or user.is_staff_member
            or user.is_lab_assistant
            or user.is_pharmacist
        )

    def get_admin_hospital_id(self):
        if self.request.user.is_super_admin:
            return None

        if not self._is_hospital_scoped_user():
            return None

        hospital_id = getattr(self.request, 'hospital_scope_id', None) or getattr(
            self.request, 'admin_hospital_id', None
        )
        if hospital_id:
            return hospital_id

        try:
            from apps.hospitals.models import HospitalAdmin, HospitalStaff

            if self.request.user.is_admin:
                return self.request.user.hospital_admin_profile.hospital_id

            return self.request.user.hospital_staff_profile.hospital_id
        except (HospitalAdmin.DoesNotExist, HospitalStaff.DoesNotExist):
            return None

    def scope_queryset_for_admin(self, queryset, hospital_field='hospital_id'):
        if self.request.user.is_super_admin:
            return queryset

        if not self._is_hospital_scoped_user():
            return queryset

        hospital_id = self.get_admin_hospital_id()
        if not hospital_id:
            return queryset.none()

        return queryset.filter(**{hospital_field: hospital_id})
