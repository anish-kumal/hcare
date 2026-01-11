from django.shortcuts import redirect, get_object_or_404
from django.views.generic import DetailView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from apps.patients.models import Patient, PatientAppointment
from .forms import PatientProfileForm


class PatientOnlyMixin(LoginRequiredMixin):
    """Restrict views to patient users only"""
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_patient:
            messages.error(request, 'Only patients can access this page.')
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)


class PatientProfileView(PatientOnlyMixin, DetailView):
    """View patient profile and manage appointments"""
    model = Patient
    template_name = 'patients/patient_profile.html'
    context_object_name = 'patient'
    
    def get_object(self, queryset=None):
        """Get the patient profile for the current user"""
        return Patient.objects.get(user=self.request.user)
    
    def post(self, request, *args, **kwargs):
        """Handle profile update"""
        patient = self.get_object()
        form = PatientProfileForm(request.POST, instance=patient)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('patients:patient_profile')
        else:
            messages.error(request, 'Please correct the errors below.')
            return self.get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.object
        
        # Get upcoming appointments
        context['upcoming_appointments'] = PatientAppointment.objects.filter(
            patient=patient,
            appointment_date__gte=timezone.now().date(),
            status__in=['SCHEDULED', 'CONFIRMED']
        ).select_related('doctor', 'doctor__user', 'doctor__specialization').order_by('appointment_date', 'appointment_time')
        
        # Get past appointments
        context['past_appointments'] = PatientAppointment.objects.filter(
            patient=patient,
            appointment_date__lt=timezone.now().date()
        ).select_related('doctor', 'doctor__user', 'doctor__specialization').order_by('-appointment_date', '-appointment_time')
        
        # Get form
        context['form'] = PatientProfileForm(instance=patient)
        
        return context
