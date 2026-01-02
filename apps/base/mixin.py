from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages


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
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)
    

