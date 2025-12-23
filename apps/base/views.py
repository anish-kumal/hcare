from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

# Create your views here.

class IndexView(TemplateView):
    """Render the home page"""
    template_name = 'patient/index.html'


class SuperAdminDashboardView(LoginRequiredMixin, TemplateView):
    """Super Admin Dashboard"""
    template_name = 'super_admin/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_super_admin:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """Admin Dashboard"""
    template_name = 'admin/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class DoctorDashboardView(LoginRequiredMixin, TemplateView):
    """Doctor Dashboard"""
    template_name = 'doctor/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_doctor:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class PatientDashboardView(LoginRequiredMixin, TemplateView):
    """Patient Dashboard"""
    template_name = 'patient/index.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_patient:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class LabAssistantDashboardView(LoginRequiredMixin, TemplateView):
    """Lab Assistant Dashboard"""
    template_name = 'lab_assistant/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_lab_assistant:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)
