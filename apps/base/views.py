from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from .mixin import RoleRequiredMixin

# Create your views here.




class IndexView(RoleRequiredMixin, TemplateView):
    """Render the home page"""
    template_name = 'patient/index.html'



class AdministrView(TemplateView):
    """Render the hospital onboarding landing page"""
    template_name = 'administer/index_administer.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            if user.is_super_admin:
                return redirect(reverse_lazy('super_admin_dashboard'))
            elif user.is_admin:
                return redirect(reverse_lazy('admin_dashboard'))
            elif user.is_doctor:
                return redirect(reverse_lazy('doctor_dashboard'))
            elif user.is_lab_assistant:
                return redirect(reverse_lazy('lab_assistant_dashboard'))
        return super().dispatch(request, *args, **kwargs)


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


class Custom404View(View):
    def dispatch(self, request, *args, **kwargs):
        return render(request, '404.html', status=404)


class Custom500View(View):
    def dispatch(self, request, *args, **kwargs):
        return render(request, '500.html', status=500)
