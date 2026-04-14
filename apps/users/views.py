from django.shortcuts import redirect
from django.views.generic import CreateView, ListView, DetailView, UpdateView, DeleteView, FormView
from django.views import View
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import logout, update_session_auth_hash
from django.urls import reverse, reverse_lazy, NoReverseMatch
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Max, Q
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date
from django.utils.html import strip_tags
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from axes.models import AccessAttempt
from axes.utils import reset as axes_reset
from .forms import (
    PasswordChangeForm,
    UserRegistrationForm,
    UserLoginForm,
    UserManagementForm,
    UserSelfProfileForm,
)
from .models import User
from apps.hospitals.models import HospitalAdmin, HospitalStaff

from apps.base.mixin import SuperAdminAndAdminOnlyMixin, AdminOnlyMixin, SuperAdminOnlyMixin


MANAGEABLE_USER_TYPES = [
    User.UserType.STAFF,
    User.UserType.LAB_ASSISTANT,
    User.UserType.PHARMACIST,
]


class StaffPortalAccessMixin(LoginRequiredMixin):
    """Allow only non-patient staff portal roles used in administer login."""

    login_url = 'users:administer_login'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return self.handle_no_permission()

        allowed = (
            user.is_super_admin
            or user.is_admin
            or user.is_staff_member
            or user.is_lab_assistant
            or user.is_pharmacist
            or user.is_doctor
        )
        if not allowed:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('index')

        return super().dispatch(request, *args, **kwargs)


class ManageableUserScopeMixin:
    """Scope manageable users by role: super admin sees all, admin sees own hospital only."""

    def get_manageable_user_queryset(self):
        queryset = User.objects.filter(user_type__in=MANAGEABLE_USER_TYPES).order_by('-created')

        if not self.request.user.is_super_admin:
            hospital_id = getattr(self.request, 'hospital_scope_id', None) or getattr(
                self.request, 'admin_hospital_id', None
            )

            if not hospital_id:
                try:
                    if self.request.user.is_admin:
                        hospital_id = self.request.user.hospital_admin_profile.hospital_id
                    elif (
                        self.request.user.is_staff_member
                        or self.request.user.is_lab_assistant
                        or self.request.user.is_pharmacist
                    ):
                        hospital_id = self.request.user.hospital_staff_profile.hospital_id
                except (HospitalAdmin.DoesNotExist, HospitalStaff.DoesNotExist):
                    return User.objects.none()

            if not hospital_id:
                return User.objects.none()

            queryset = queryset.filter(hospital_staff_profile__hospital_id=hospital_id)

        return queryset


class UserRegisterView(CreateView):
    """
    Class-based view for user registration
    """
    model = User
    form_class = UserRegistrationForm
    template_name = 'patients/register.html'
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        self.object = form.save()
        uid = urlsafe_base64_encode(force_bytes(self.object.pk))
        token = default_token_generator.make_token(self.object)
        try:
            activation_path = reverse('users:activate_account', kwargs={'uidb64': uid, 'token': token})
        except NoReverseMatch:
            activation_path = reverse('activate_account', kwargs={'uidb64': uid, 'token': token})

        activation_url = self.request.build_absolute_uri(activation_path)

        context = {
            'user_name': self.object.get_full_name() or self.object.username,
            'activation_url': activation_url,
            'support_email': settings.DEFAULT_FROM_EMAIL,
        }

        try:
            html_message = render_to_string('email/account_activation_email.html', context)
            plain_message = strip_tags(html_message)
            send_mail(
                subject='Verify Your Health Care Account',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.object.email],
                html_message=html_message,
                fail_silently=False,
            )
            messages.success(
                self.request,
                'Registration successful. Please check your email and verify your account before login.'
            )
        except Exception:
            self.object.delete()
            messages.error(
                self.request,
                'Registration failed because verification email could not be sent. Please try again.'
            )
            return self.form_invalid(form)

        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, 'Registration failed.')
        return super().form_invalid(form)


class ActivateAccountView(View):
    """Activate a newly registered account from email verification link."""

    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user and default_token_generator.check_token(user, token):
            if user.is_verified:
                messages.info(request, 'Your account is already verified. You can login now.')
            else:
                user.is_verified = True
                user.save(update_fields=['is_verified'])
                messages.success(request, 'Your account has been verified successfully. You can now login.')
        else:
            messages.error(request, 'Verification link is invalid or expired. Please register again.')

        return redirect('users:login')

class UserLoginView(LoginView):
    """
    Class-based view for user login
    """
    form_class = UserLoginForm
    template_name = 'base/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('patient_dashboard')
    
    def form_valid(self, form):
        """
        If the form is valid, log the user in only if they are a patient and active.
        Any other role or inactive user is rejected with an error message.
        """
        user = form.get_user()
        if not user.is_verified:
            logout(self.request)
            messages.error(
                self.request,
                'Account with this email/username exists but is not verified. Please check your email for verification instructions or contact support.'
            )
            return redirect(reverse_lazy('users:login'))

        if not user.is_patient:
            logout(self.request)
            messages.error(
                self.request,
                'Unauthorized: This login is for patients only.'
            )
            return redirect(reverse_lazy('users:login'))

        if user.is_default_password:
            messages.warning(
                self.request,
                'Please change your default password before continuing.'
            )
            return redirect(f"{reverse('otp:request')}?source=patient")

        messages.success(
            self.request,
            f'Welcome back, {user.get_full_name() or user.username}!'
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """
        If the form is invalid, display error message
        """
        messages.error(
            self.request,
            'Invalid email/username or password. Please try again.as'
        )
        return super().form_invalid(form)


class AdministerLoginView(LoginView):
    """
    Login view for all non-patient staff (admins, doctors, lab assistants, etc.).
    Patients are rejected as unauthorized.
    """
    form_class = UserLoginForm
    template_name = 'base/login_administer.html'
    redirect_authenticated_user = True

    def _get_associated_hospital(self, user):
        if user.is_super_admin:
            return None

        try:
            if user.is_admin and hasattr(user, 'hospital_admin_profile'):
                return user.hospital_admin_profile.hospital

            if user.is_doctor and hasattr(user, 'doctor_profile'):
                return user.doctor_profile.hospital

            if user.is_staff_member or user.is_lab_assistant or user.is_pharmacist:
                return user.hospital_staff_profile.hospital
        except (HospitalAdmin.DoesNotExist, HospitalStaff.DoesNotExist):
            return None

        return None

    def get_success_url(self):
        user = self.request.user
        if user.is_super_admin:
            return reverse_lazy('super_admin_dashboard')
        elif user.is_admin:
            return reverse_lazy('admin_dashboard')
        elif user.is_doctor:
            return reverse_lazy('doctor_dashboard')
        elif user.is_lab_assistant:
            return reverse_lazy('lab_assistant_dashboard')
        elif user.is_pharmacist:
            return reverse_lazy('pharmacist_dashboard')
        elif user.is_staff_member:
            return reverse_lazy('staff_dashboard')
        else:
            return reverse_lazy('index')

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_active:
            logout(self.request)
            messages.error(
                self.request,
                'Invalid email/username or password. Please try again.'
            )
            return redirect(reverse_lazy('users:administer_login'))

        if user.is_patient:
            logout(self.request)
            messages.error(
                self.request,
                'Invalid email/username or password. Please try again.'
            )
            return redirect(reverse_lazy('users:administer_login'))

        hospital = self._get_associated_hospital(user)
        if hospital and not hospital.is_active:
            messages.error(
                self.request,
                'Your hospital is currently inactive. Please contact the super admin.'
            )
            return redirect(reverse_lazy('users:administer_login'))

        if user.is_default_password:
            messages.warning(
                self.request,
                'Please change your default password before continuing.'
            )
            return redirect(f"{reverse('otp:request')}?source=administer")

        messages.success(
            self.request,
            f'Welcome back, {user.get_full_name() or user.username}!'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request,
            'Invalid email/username or password. Please try again.'
        )
        return super().form_invalid(form)


class UserLogoutView(LoginRequiredMixin, LogoutView):
    """
    Class-based view for user logout
    """
    next_page = reverse_lazy('index')  # Redirect to home after logout
    http_method_names = ['get', 'post']  # Allow both GET and POST
    
    def get(self, request, *args, **kwargs):
        messages.success(request, 'You have been logged out successfully.')
        return self.post(request, *args, **kwargs)
    

class AdministerLogoutView(LoginRequiredMixin, LogoutView):
    """
    Class-based view for user logout
    """
    next_page = reverse_lazy('administer')  # Redirect to home after logout
    http_method_names = ['get', 'post']  # Allow both GET and POST
    
    def get(self, request, *args, **kwargs):
        messages.success(request, 'You have been logged out successfully.')
        return self.post(request, *args, **kwargs)



class UserListView(ManageableUserScopeMixin, SuperAdminAndAdminOnlyMixin, ListView):
    """List all users for Super Admin
    Admin can only see users from their hospital
    """
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 10

    def _base_queryset(self):
        return self.get_manageable_user_queryset()
    
    def get_queryset(self):
        queryset = self._base_queryset()

        search_query = self.request.GET.get('search', '')
        user_type = self.request.GET.get('user_type', '')
        joined_date = self.request.GET.get('joined_date', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        if user_type in MANAGEABLE_USER_TYPES:
            queryset = queryset.filter(user_type=user_type)

        if joined_date:
            parsed_joined_date = parse_date(joined_date)
            if parsed_joined_date:
                queryset = queryset.filter(created__date=parsed_joined_date)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = self._base_queryset()
        user_counts = users.aggregate(
            total=Count('id'),
            staff=Count('id', filter=Q(user_type=User.UserType.STAFF)),
            lab_assistant=Count('id', filter=Q(user_type=User.UserType.LAB_ASSISTANT)),
            pharmacist=Count('id', filter=Q(user_type=User.UserType.PHARMACIST)),
        )
        context['search_query'] = self.request.GET.get('search', '')
        context['user_type_filter'] = self.request.GET.get('user_type', '')
        context['joined_date_filter'] = self.request.GET.get('joined_date', '')
        context['user_types'] = [
            choice for choice in User.UserType.choices
            if choice[0] in MANAGEABLE_USER_TYPES
        ]
        context['analytics_cards'] = [
            {'label': 'Total Users', 'value': user_counts['total'],  'icon': 'group'},
            {'label': 'Lab Technicians', 'value': user_counts['lab_assistant'],  'icon': 'science'},
            {'label': 'Staff', 'value': user_counts['staff'],  'icon': 'badge'},
            {'label': 'Pharmacists', 'value': user_counts['pharmacist'], 'icon': 'medication'},
        ]
        return context


class AxesLockListView(SuperAdminOnlyMixin, ListView):
    """Show grouped Axes lockout rows for super admin and allow unlock actions."""
    model = AccessAttempt
    template_name = 'super_admin/axes_lock_list.html'
    context_object_name = 'locked_users'
    paginate_by = 15

    def get_queryset(self):
        queryset = (
            AccessAttempt.objects.exclude(username__isnull=True)
            .exclude(username='')
            .values('username')
            .annotate(
                attempts=Count('id'),
                failures=Max('failures_since_start'),
                last_attempt=Max('attempt_time'),
                last_ip=Max('ip_address'),
            )
            .order_by('-last_attempt', 'username')
        )

        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(username__icontains=search_query)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class AxesUnlockUserView(SuperAdminOnlyMixin, View):
    """Unlock a user by username using Axes reset helper."""

    def post(self, request, username, *args, **kwargs):
        removed_count = axes_reset(username=username)
        if removed_count:
            messages.success(request, f'Unlocked {username} successfully.')
        else:
            messages.info(request, f'No Axes lockout entries found for {username}.')
        return redirect('users:axes_lock_list')

class UserCreateView(AdminOnlyMixin, CreateView):
    """Create user for Super Admin
    Admin can only create users for their hospital
    """
    model = User
    form_class = UserManagementForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user_list')
    
    def form_valid(self, form):
        try:
            hospital_admin = self.request.user.hospital_admin_profile
        except HospitalAdmin.DoesNotExist:
            messages.error(self.request, 'Admin hospital profile not found.')
            return redirect('admin_dashboard')

        with transaction.atomic():
            self.object = form.save()
            password = form.cleaned_data.get('password')

            if password:
                self.object.is_default_password = True
                self.object.save(update_fields=['is_default_password'])

            if self.object.user_type in [
                User.UserType.STAFF,
                User.UserType.LAB_ASSISTANT,
                User.UserType.PHARMACIST,
            ]:
                HospitalStaff.objects.update_or_create(
                    user=self.object,
                    defaults={'hospital': hospital_admin.hospital},
                )

        if password:
            login_url = self.request.build_absolute_uri(reverse_lazy('users:administer_login'))
            context = {
                'title': 'Your account for ',
                'user_name': self.object.get_full_name() or self.object.username,
                'hospital_name': hospital_admin.hospital.name,
                'username': self.object.username,
                'password': password,
                'login_url': login_url,
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }

            try:
                html_message = render_to_string('email/credentials_email.html', context)
                plain_message = strip_tags(html_message)
                send_mail(
                    subject='Your Staff Login Credentials',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[self.object.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                messages.success(self.request, 'User created successfully! Credentials email sent.')
            except Exception:
                messages.warning(
                    self.request,
                    'User created successfully, but credential email could not be sent. Please share credentials manually.'
                )
        else:
            messages.success(self.request, 'User created successfully!')

        return redirect(self.get_success_url())
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    
class UserDetailView(ManageableUserScopeMixin, SuperAdminAndAdminOnlyMixin, DetailView):
    """View user details for Super Admin
    Admin can only view users from their hospital"""
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'user_obj'
    slug_field = 'id'
    slug_url_kwarg = 'pk'

    def get_queryset(self):
        return self.get_manageable_user_queryset()


class UserUpdateView(ManageableUserScopeMixin, SuperAdminAndAdminOnlyMixin, UpdateView):
    """Update user for Super Admin
    Admin can only update users from their hospital"""
    model = User
    form_class = UserManagementForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user_list')
    slug_field = 'id'
    slug_url_kwarg = 'pk'

    def get_queryset(self):
        return self.get_manageable_user_queryset()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'User updated successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)




class UserDeleteView(ManageableUserScopeMixin, SuperAdminAndAdminOnlyMixin, DeleteView):
    """Delete user for Super Admin
    Admin can only delete users from their hospital"""
    model = User
    template_name = 'partials/delete.html'
    slug_field = 'id'
    slug_url_kwarg = 'pk'
    success_url = reverse_lazy('users:user_list')

    def get_queryset(self):
        return self.get_manageable_user_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        full_name = self.object.get_full_name() or self.object.username
        context['delete_page_title'] = 'Delete User - Health Care'
        context['delete_confirm_title'] = 'Delete User?'
        context['delete_confirm_message'] = (
            f'Are you sure you want to delete {full_name}? This action cannot be undone.'
        )
        context['delete_warning_text'] = (
            'Deleting this user will permanently remove all associated data.'
        )
        context['delete_button_label'] = 'Delete User'
        context['cancel_url'] = reverse_lazy('users:user_list')
        return context

    def form_valid(self, form):
        with transaction.atomic():
            self.object = self.get_object()
            HospitalStaff.objects.filter(user_id=self.object.id).delete()
            response = super().form_valid(form)

        messages.success(self.request, 'User deleted successfully!')
        return response


class PasswordChangeView(StaffPortalAccessMixin, FormView):
    """Password change page for staff portal users (doctor/admin/staff roles)."""
    template_name = 'users/password_change.html'
    form_class = PasswordChangeForm

    def get_template_names(self):
        if self.request.user.is_doctor:
            return ['doctors/password_change.html']
        return [self.template_name]

    def get_success_url(self):
        if self.request.user.is_doctor:
            return reverse_lazy('doctors:doctor_profile')
        return reverse_lazy('users:user_profile')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        new_password = form.cleaned_data.get('new_password')
        if new_password:
            self.request.user.set_password(new_password)
            self.request.user.is_default_password = False
            self.request.user.save(update_fields=['password', 'is_default_password'])
            update_session_auth_hash(self.request, self.request.user)
            messages.success(self.request, 'Password changed successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the password errors below.')
        return super().form_invalid(form)


class UserProfileView(StaffPortalAccessMixin, DetailView):
    """View own profile details for staff portal users."""
    model = User
    template_name = 'users/profile.html'

    context_object_name = 'user_obj'
    slug_field = 'id'
    slug_url_kwarg = 'pk'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_doctor:
            return redirect('doctors:doctor_profile')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user


class UserProfileUpdateView(StaffPortalAccessMixin, UpdateView):
    """Edit own profile details for non-doctor staff portal users."""

    model = User
    form_class = UserSelfProfileForm
    template_name = 'users/profile_form.html'
    success_url = reverse_lazy('users:user_profile')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_doctor:
            return redirect('doctors:doctor_profile_edit')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Profile updated successfully.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the profile errors below.')
        return super().form_invalid(form)