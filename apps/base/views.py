from django.views import View
from django.views.generic import TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from .forms import ContactMessageForm


# Create your views here.
class IndexView( TemplateView):
    """Render the home page"""
    template_name = 'patients/index.html'

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
            elif user.is_pharmacist:
                return redirect(reverse_lazy('pharmacist_dashboard'))
            elif user.is_staff_member:
                return redirect(reverse_lazy('staff_dashboard'))

        return super().dispatch(request, *args, **kwargs)



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
            elif user.is_pharmacist:
                return redirect(reverse_lazy('pharmacist_dashboard'))
            elif user.is_staff_member:
                return redirect(reverse_lazy('staff_dashboard'))
            elif user.is_patient:
                return redirect(reverse_lazy('patient_dashboard'))
        return super().dispatch(request, *args, **kwargs)


class AboutView(TemplateView):
    """Render the public About page"""
    template_name = 'base/about.html'


class TermsView(TemplateView):
    """Render the public Terms page"""
    template_name = 'base/terms.html'


class PrivacyPolicyView(TemplateView):
    """Render the public Privacy Policy page"""
    template_name = 'base/privacy_policy.html'


class ServicesView(TemplateView):
    """Render the public Services page"""
    template_name = 'base/services.html'


class ContactView(FormView):
    """Render and handle the public Contact page form"""
    template_name = 'base/contact.html'
    form_class = ContactMessageForm
    success_url = reverse_lazy('contact')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Your message has been sent successfully.")
        return super().form_valid(form)


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
    template_name = 'doctors/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_doctor:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class PatientDashboardView(LoginRequiredMixin, TemplateView):
    """Patient Dashboard"""
    template_name = 'patients/index.html'
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

class StaffDashboardView(LoginRequiredMixin, TemplateView):
    """Staff Dashboard"""
    template_name = 'staff/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff_member:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class PharmacistDashboardView(LoginRequiredMixin, TemplateView):
    """Pharmacist Dashboard"""
    template_name = 'pharmacist/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_pharmacist:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class Custom404View(View):
    def dispatch(self, request, *args, **kwargs):
        return render(request, 'custom/404.html', status=404)


class Custom500View(View):
    def dispatch(self, request, *args, **kwargs):
        return render(request, 'custom/500.html', status=500)
