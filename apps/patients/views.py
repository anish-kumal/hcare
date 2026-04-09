from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DetailView, UpdateView, DeleteView, ListView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse_lazy

from apps.base.mixin import SuperAdminAndAdminOnlyMixin
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

    def _get_user_hospital_id(self):
        user = self.request.user

        if user.is_super_admin:
            return None

        if user.is_admin and hasattr(user, 'hospital_admin_profile'):
            return user.hospital_admin_profile.hospital_id

        if user.is_doctor and hasattr(user, 'doctor_profile'):
            return user.doctor_profile.hospital_id

        if user.is_staff and hasattr(user, 'hospital_staff_profile'):
            return user.hospital_staff_profile.hospital_id

        return -1

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

        if self._get_user_hospital_id() == -1:
            raise PermissionDenied("Your account is not linked to a hospital.")

        return super().dispatch(request, *args, **kwargs)

    def get_hospital_scoped_queryset(self):
        queryset = Patient.objects.select_related('user', 'hospital').order_by('-created')
        hospital_id = self._get_user_hospital_id()
        if hospital_id is None:
            return queryset
        return queryset.filter(hospital_id=hospital_id)


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
        ).order_by('-created')

        context['prescriptions'] = Prescription.objects.filter(
            appointment__patient=patient,
        ).select_related(
            'appointment',
            'appointment__doctor__user',
        ).prefetch_related('medicines').order_by('-created')
        
        # Get upcoming appointments
        context['upcoming_appointments'] = PatientAppointment.objects.filter(
            patient=patient,
            appointment_date__gte=timezone.now().date(),
            status__in=['SCHEDULED', 'CONFIRMED', 'IN_PROGRESS', 'FOLLOW_UP']
        ).select_related('doctor', 'doctor__user').order_by('appointment_date', 'appointment_time')
        
        # Get past appointments
        context['past_appointments'] = PatientAppointment.objects.filter(
            patient=patient,
            appointment_date__lt=timezone.now().date()
        ).select_related('doctor', 'doctor__user').order_by('-appointment_date', '-appointment_time')

        return context


class PatientProfileEditView(PatientOnlyMixin, UpdateView):
    """Allow patients to edit their own profile."""
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
        context['patient_form'] = kwargs.get('patient_form') or PatientProfileForm(instance=self.object)
        context['account_form'] = kwargs.get('account_form') or PatientAccountForm(instance=self.request.user)
        context['password_form'] = kwargs.get('password_form') or PasswordChangeForm(self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action', 'profile')

        if action == 'account':
            account_form = PatientAccountForm(request.POST, instance=request.user)
            if account_form.is_valid():
                account_form.save()
                messages.success(request, 'Account details updated successfully!')
                return redirect('patients:patient_profile')

            messages.error(request, 'Please correct the account details below.')
            return self.render_to_response(self.get_context_data(account_form=account_form))

        if action == 'password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                new_password = password_form.cleaned_data.get('new_password')
                request.user.set_password(new_password)
                request.user.is_default_password = False
                request.user.save(update_fields=['password', 'is_default_password'])
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully!')
                return redirect('patients:patient_profile')

            messages.error(request, 'Please correct the password errors below.')
            return self.render_to_response(self.get_context_data(password_form=password_form))

        patient_form = PatientProfileForm(request.POST, request.FILES, instance=self.object)
        if patient_form.is_valid():
            patient_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('patients:patient_profile')

        messages.error(request, 'Please correct the profile errors below.')
        return self.render_to_response(self.get_context_data(patient_form=patient_form))

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


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


class PatientCreateView(LoginRequiredMixin, CreateView):
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

class PatientDetailView(PatientHospitalScopedMixin, DetailView):
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


    
class PatientListView(PatientHospitalScopedMixin, ListView):
    """List all patients - For Admin and Super Admin"""
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 10
    
    def get_queryset(self):
        """Get all patients with optional search"""
        queryset = self.get_hospital_scoped_queryset()
        search_query = self.request.GET.get('search', '').strip()
        is_active_filter = self.request.GET.get('is_active', '').strip().lower()

        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query)
                | Q(user__last_name__icontains=search_query)
                | Q(user__username__icontains=search_query)
                | Q(user__email__icontains=search_query)
                | Q(contact_number__icontains=search_query)
                | Q(city__icontains=search_query)
            )

        if is_active_filter == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active_filter == 'false':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '').strip()
        context['is_active_filter'] = self.request.GET.get('is_active', '').strip().lower()
        return context

class PatientDeleteView(SuperAdminAndAdminOnlyMixin, DeleteView):
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

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Patient deleted successfully!')
        return super().delete(request, *args, **kwargs)