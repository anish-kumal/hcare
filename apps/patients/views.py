from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DetailView, UpdateView, DeleteView, ListView
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse_lazy

from apps.base.mixin import SuperAdminAndAdminOnlyMixin, SuperAdminAdminStaffOnlyMixin,  AdminStaffOnlyMixin
from apps.appointments.models import Prescription
from apps.patients.models import Patient, PatientAppointment
from apps.users.forms import PasswordChangeForm
from .forms import PatientAccountForm, PatientCreateProfileForm, PatientProfileForm, PatientUserForm

User = get_user_model()


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


class PatientHospitalScopedMixin(LoginRequiredMixin):
    """Allow super admin/admin/doctor/staff and scope patient data by hospital."""
    login_url = 'users:login'

    def _get_user_hospital(self):
        user = self.request.user

        if user.is_super_admin:
            return None

        if user.is_admin and hasattr(user, 'hospital_admin_profile'):
            return user.hospital_admin_profile.hospital

        if user.is_doctor and hasattr(user, 'doctor_profile'):
            return user.doctor_profile.hospital

        if user.is_staff_member and hasattr(user, 'hospital_staff_profile'):
            return user.hospital_staff_profile.hospital

        return -1

    def _get_user_hospital_id(self):
        hospital = self._get_user_hospital()
        if hospital in (None, -1):
            return hospital
        return hospital.id

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        allowed_roles = {
            User.UserType.SUPER_ADMIN,
            User.UserType.ADMIN,
            User.UserType.DOCTOR,
            User.UserType.STAFF,
        }
        if request.user.user_type not in allowed_roles:
            raise PermissionDenied("You don't have permission to access this page.")

        hospital = self._get_user_hospital()
        if hospital == -1:
            raise PermissionDenied("Your account is not linked to a hospital.")

        if hospital and not hospital.is_active:
            raise PermissionDenied("Your hospital is currently inactive. Please contact the super admin.")

        return super().dispatch(request, *args, **kwargs)

    def get_hospital_scoped_queryset(self):
        queryset = Patient.objects.select_related('user', 'hospital').order_by('-created')
        hospital_id = self._get_user_hospital_id()
        if hospital_id is None:
            return queryset
        return queryset.filter(
            Q(hospital_id=hospital_id)
            | Q(appointments__hospital_id=hospital_id)
        ).distinct()


class PatientProfileView(PatientOnlyMixin, DetailView):
    """View patient profile and appointments."""
    model = Patient
    template_name = 'patients/patient_profile.html'
    context_object_name = 'patient'

    def dispatch(self, request, *args, **kwargs):
        if not Patient.objects.filter(user=request.user).exists():
            messages.error(
                request,
                'Please complete your patient profile to continue.'
            )
            return redirect('patients:patient_profile_create')

        return super().dispatch(request, *args, **kwargs)
    
    def get_object(self, queryset=None):
        """Get the patient profile for the current user"""
        return get_object_or_404(Patient, user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.object

        context['medical_reports'] = patient.medical_reports.select_related(
            'primary_hospital',
            'uploaded_by',
        ).order_by('-created')[:5]

        context['prescriptions'] = Prescription.objects.filter(
            appointment__patient=patient,
        ).select_related(
            'appointment',
            'appointment__doctor__user',
        ).prefetch_related('medicines').order_by('-created')[:5]
        
        # Get upcoming appointments
        context['upcoming_appointments'] = PatientAppointment.objects.filter(
            patient=patient,
            appointment_date__gte=timezone.now().date(),
            status__in=['SCHEDULED', 'CONFIRMED', 'IN_PROGRESS', 'FOLLOW_UP']
        ).select_related('doctor', 'doctor__user').order_by('appointment_date', 'appointment_time')[:5]

        # Get past appointments (only COMPLETED or CANCELLED, limit 5)
        context['past_appointments'] = PatientAppointment.objects.filter(
            patient=patient,
            status__in=['COMPLETED', 'CANCELLED']
        ).select_related('doctor', 'doctor__user').order_by('-appointment_date', '-appointment_time')[:5]

        return context
    


class PatientUpcomingAppointmentsView(PatientOnlyMixin, ListView):
    """View upcoming appointments for patient profile with pagination."""
    model = PatientAppointment
    template_name = 'patients/patient_profile_upcoming_appointments.html'
    context_object_name = 'appointments'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if not Patient.objects.filter(user=request.user).exists():
            messages.error(
                request,
                'Please complete your patient profile to continue.'
            )
            return redirect('patients:patient_profile_create')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Get upcoming appointments for the current patient"""
        patient = get_object_or_404(Patient, user=self.request.user)
        return PatientAppointment.objects.filter(
            patient=patient,
            appointment_date__gte=timezone.now().date(),
            status__in=['SCHEDULED', 'CONFIRMED', 'IN_PROGRESS', 'FOLLOW_UP']
        ).select_related('doctor', 'doctor__user').order_by('appointment_date', 'appointment_time')
    
class PatientPastAppointmentsView(PatientOnlyMixin, ListView):
    """View past appointments for patient profile with pagination."""
    model = PatientAppointment
    template_name = 'patients/patient_profile_past_appointments.html'
    context_object_name = 'appointments'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if not Patient.objects.filter(user=request.user).exists():
            messages.error(
                request,
                'Please complete your patient profile to continue.'
            )
            return redirect('patients:patient_profile_create')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Get past appointments for the current patient"""
        patient = get_object_or_404(Patient, user=self.request.user)
        return PatientAppointment.objects.filter(
            patient=patient,
            status__in=['COMPLETED', 'CANCELLED']
        ).select_related('doctor', 'doctor__user').order_by('-appointment_date', '-appointment_time')
    
class PatientMedicalReportsView(PatientOnlyMixin, ListView):
    """View medical reports for patient profile with pagination."""
    model = Patient
    template_name = 'patients/patient_profile_medical_reports.html'
    context_object_name = 'medical_reports'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if not Patient.objects.filter(user=request.user).exists():
            messages.error(
                request,
                'Please complete your patient profile to continue.'
            )
            return redirect('patients:patient_profile_create')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Get medical reports for the current patient"""
        patient = get_object_or_404(Patient, user=self.request.user)
        return patient.medical_reports.select_related(
            'primary_hospital',
            'uploaded_by',
        ).order_by('-created')
    
class PatientPrescriptionsView(PatientOnlyMixin, ListView):
    """View prescriptions for patient profile with pagination."""
    model = Prescription
    template_name = 'patients/patient_profile_prescriptions.html'
    context_object_name = 'prescriptions'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if not Patient.objects.filter(user=request.user).exists():
            messages.error(
                request,
                'Please complete your patient profile to continue.'
            )
            return redirect('patients:patient_profile_create')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Get prescriptions for the current patient"""
        patient = get_object_or_404(Patient, user=self.request.user)
        return Prescription.objects.filter(
            appointment__patient=patient,
        ).select_related(
            'appointment',
            'appointment__doctor__user',
        ).prefetch_related('medicines').order_by('-created')
    




class PatientProfileEditView(PatientOnlyMixin, UpdateView):
    """Allow patients to edit their own personal profile."""
    model = Patient
    form_class = PatientProfileForm
    template_name = 'patients/patient_profile_edit.html'
    context_object_name = 'patient'
    success_url = reverse_lazy('patients:patient_profile')

    def dispatch(self, request, *args, **kwargs):
        if not Patient.objects.filter(user=request.user).exists():
            messages.error(
                request,
                'Please complete your patient profile to continue.'
            )
            return redirect('patients:patient_profile_create')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return get_object_or_404(Patient, user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient_form'] = context.get('form')
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Personal profile updated successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the personal profile errors below.')
        return super().form_invalid(form)


class PatientAccountEditView(PatientOnlyMixin, View):
    """Edit patient account details (username/email) on a separate page."""

    template_name = 'patients/patient_account_edit.html'

    def get(self, request, *args, **kwargs):
        if not Patient.objects.filter(user=request.user).exists():
            messages.error(request, 'Please complete your patient profile to continue.')
            return redirect('patients:patient_profile_create')

        form = PatientAccountForm(instance=request.user)
        return render(request, self.template_name, {'account_form': form})

    def post(self, request, *args, **kwargs):
        if not Patient.objects.filter(user=request.user).exists():
            messages.error(request, 'Please complete your patient profile to continue.')
            return redirect('patients:patient_profile_create')

        form = PatientAccountForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account details updated successfully!')
            return redirect('patients:patient_profile')

        messages.error(request, 'Please correct the account details below.')
        return render(request, self.template_name, {'account_form': form})


class PatientPasswordChangeView(PatientOnlyMixin, View):
    """Change patient password on a separate page."""

    template_name = 'patients/patient_password_change.html'

    def get(self, request, *args, **kwargs):
        if not Patient.objects.filter(user=request.user).exists():
            messages.error(request, 'Please complete your patient profile to continue.')
            return redirect('patients:patient_profile_create')

        form = PasswordChangeForm(request.user)
        return render(request, self.template_name, {'password_form': form})

    def post(self, request, *args, **kwargs):
        if not Patient.objects.filter(user=request.user).exists():
            messages.error(request, 'Please complete your patient profile to continue.')
            return redirect('patients:patient_profile_create')

        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            new_password = form.cleaned_data.get('new_password')
            request.user.set_password(new_password)
            request.user.is_default_password = False
            request.user.save(update_fields=['password', 'is_default_password'])
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully!')
            return redirect('patients:patient_profile')

        messages.error(request, 'Please correct the password errors below.')
        return render(request, self.template_name, {'password_form': form})


class PatientSelfProfileCreateView(PatientOnlyMixin, CreateView):
    """Allow logged-in patients to create their own profile once."""
    model = Patient
    form_class = PatientCreateProfileForm
    template_name = 'patients/patient_profile_create.html'

    def dispatch(self, request, *args, **kwargs):
        if Patient.objects.filter(user=request.user).exists():
            return redirect('patients:patient_profile')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        patient = form.save(commit=False)
        patient.user = self.request.user
        patient.save()
        messages.success(self.request, 'Your patient profile has been created successfully!')
        return redirect('patients:patient_profile')

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class PatientCreateView(AdminStaffOnlyMixin, CreateView):
    """
    Create Patient - Both User and Patient Profile in one page
    Hospital Admin and Staff can create patients
    """

    template_name = 'patients/patient_create.html'
    login_url = 'users:login'
    form_class = PatientCreateProfileForm

    def _get_request_hospital(self, request):
        if request.user.is_admin and hasattr(request.user, 'hospital_admin_profile'):
            return request.user.hospital_admin_profile.hospital

        if request.user.is_staff_member and hasattr(request.user, 'hospital_staff_profile'):
            return request.user.hospital_staff_profile.hospital

        return None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        allowed_roles = {User.UserType.ADMIN, User.UserType.STAFF}
        if request.user.user_type not in allowed_roles:
            messages.error(request, 'You do not have permission to create patients.')
            raise PermissionDenied

        if self._get_request_hospital(request) is None:
            messages.error(request, 'Your account is not linked to a hospital.')
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['user_form'] = kwargs.get('user_form') or PatientUserForm(prefix='user')
        context['patient_form'] = kwargs.get('patient_form') or PatientCreateProfileForm(prefix='patient')

        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        user_form = PatientUserForm(request.POST, prefix='user')
        patient_form = PatientCreateProfileForm(
            request.POST,
            request.FILES,
            prefix='patient',
        )

        if user_form.is_valid() and patient_form.is_valid():
            try:
                with transaction.atomic():
                    user = user_form.save(commit=False)
                    user.user_type = User.UserType.PATIENT
                    user.is_default_password = True
                    user.save()

                    password = user_form.cleaned_data.get('password')
                    user.set_password(password)
                    user.save(update_fields=['password', 'is_default_password'])

                    patient = patient_form.save(commit=False)
                    patient.user = user
                    patient.hospital = self._get_request_hospital(request)
                    patient.save()

                if password:
                    hospital_name = patient.hospital.name if patient.hospital else 'Health Care System'

                    login_url = request.build_absolute_uri(reverse_lazy('users:login'))
                    context = {
                        'title': 'Your patient account for ',
                        'user_name': user.get_full_name() or user.username,
                        'hospital_name': hospital_name,
                        'username': user.username,
                        'password': password,
                        'login_url': login_url,
                        'support_email': settings.DEFAULT_FROM_EMAIL,
                    }

                    try:
                        html_message = render_to_string('email/credentials_email.html', context)
                        plain_message = strip_tags(html_message)
                        send_mail(
                            subject='Your Patient Login Credentials',
                            message=plain_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            html_message=html_message,
                            fail_silently=False,
                        )
                        messages.success(request, 'Patient created successfully! Credentials email sent.')
                    except Exception:
                        messages.warning(
                            request,
                            'Patient created successfully, but credential email could not be sent. Please share credentials manually.'
                        )
                else:
                    messages.success(request, f'Patient {user.get_full_name() or user.username} created successfully!')

                return redirect('patients:patient_list')

            except IntegrityError as exc:
                messages.error(request, f'Error creating patient: {exc}')

        messages.error(request, 'Please correct the errors below.')
        return self.render_to_response(
            self.get_context_data(
                user_form=user_form,
                patient_form=patient_form,
            )
        )

class PatientDetailView(PatientHospitalScopedMixin, SuperAdminAdminStaffOnlyMixin, DetailView):
    """View patient details - For Admin and Super Admin"""
    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'
    slug_field = 'id'
    slug_url_kwarg = 'pk'

    def get_queryset(self):
        return self.get_hospital_scoped_queryset()

    def get_object(self, queryset=None):
        """Get patient by ID"""
        if queryset is None:
            queryset = self.get_queryset()
        return get_object_or_404(queryset, id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.object
        today = timezone.now().date()
        age = today.year - patient.date_of_birth.year
        if (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day):
            age -= 1
        context['patient_age'] = age
        return context
    
class PatientUpdateView(PatientHospitalScopedMixin, UpdateView):
    """Update patient details - For Admin and Super Admin"""
    model = Patient
    form_class = PatientCreateProfileForm
    template_name = 'patients/patient_update.html'
    context_object_name = 'patient'
    slug_field = 'id'
    slug_url_kwarg = 'pk'
    success_url = reverse_lazy('patients:patient_list')

    def get_queryset(self):
        return self.get_hospital_scoped_queryset()
    
    def get_object(self, queryset=None):
        """Get patient by ID"""
        if queryset is None:
            queryset = self.get_queryset()
        return get_object_or_404(queryset, id=self.kwargs['pk'])

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Patient updated successfully!')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


    
class PatientListView(PatientHospitalScopedMixin, SuperAdminAdminStaffOnlyMixin, ListView):
    """List all patients - For Admin and Super Admin"""
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 10

    def _base_queryset(self):
        return self.get_hospital_scoped_queryset()
    
    def get_queryset(self):
        """Get all patients with optional search"""
        queryset = self._base_queryset()
        search_query = self.request.GET.get('search', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query)
                | Q(user__last_name__icontains=search_query)
                | Q(user__username__icontains=search_query)
                | Q(user__email__icontains=search_query)
                | Q(contact_number__icontains=search_query)
                | Q(city__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '').strip()
        return context

class PatientDeleteView(SuperAdminAndAdminOnlyMixin, SuperAdminAdminStaffOnlyMixin, DeleteView):
    """Delete patient - For Admin and Super Admin"""
    model = Patient
    template_name = 'partials/delete.html'
    context_object_name = 'patient'
    slug_field = 'id'
    slug_url_kwarg = 'pk'
    success_url = reverse_lazy('patients:patient_list')
    
    def get_object(self, queryset=None):
        """Get patient by ID"""
        return Patient.objects.get(id=self.kwargs['pk'])

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_super_admin:
            messages.error(request, 'Only super admin can delete patients.')
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        full_name = self.object.user.get_full_name() or self.object.user.username
        context['delete_page_title'] = 'Delete Patient - Health Care'
        context['delete_confirm_title'] = 'Delete Patient?'
        context['delete_confirm_message'] = (
            f'Are you sure you want to delete {full_name}? This action cannot be undone.'
        )
        context['delete_warning_text'] = (
            'Deleting this patient will permanently remove profile and related data.'
        )
        context['delete_button_label'] = 'Delete Patient'
        context['cancel_url'] = reverse_lazy('patients:patient_list')
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, 'Patient deleted successfully!')
            return response
        except ProtectedError:
            messages.error(
                self.request,
                'Patient cannot be deleted because it has related appointments or records.'
            )
            return redirect(self.success_url)