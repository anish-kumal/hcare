from django.shortcuts import redirect
from django.views.generic import CreateView, ListView, DetailView, UpdateView, DeleteView, FormView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import logout, update_session_auth_hash
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from .forms import PasswordChangeForm, UserRegistrationForm, UserLoginForm, UserManagementForm
from .models import User
from apps.hospitals.models import HospitalAdmin, HospitalStaff

from apps.base.mixin import SuperAdminAndAdminOnlyMixin, AdminOnlyMixin


MANAGEABLE_USER_TYPES = [
    User.UserType.STAFF,
    User.UserType.LAB_ASSISTANT,
    User.UserType.PHARMACIST,
]


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
        response = super().form_valid(form)
        messages.success(self.request, 'Registration successful! Please log in with your new account.')
        return response
    def form_invalid(self, form):
        messages.error(self.request, 'Registration failed.')
        return super().form_invalid(form)

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
        If the form is valid, log the user in only if they are a patient.
        Any other role is rejected with an unauthorized message.
        """
        user = form.get_user()
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
            'Invalid email/username or password. Please try again.'
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
        elif user.is_lab_assistant or user.is_pharmacist:
            return reverse_lazy('lab_assistant_dashboard')
        else:
            return reverse_lazy('index')

    def form_valid(self, form):
        user = form.get_user()
        if user.is_patient:
            logout(self.request)
            messages.error(
                self.request,
                'Invalid valid email/username or password. Please try again.'
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
        
        if search_query:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        if user_type in MANAGEABLE_USER_TYPES:
            queryset = queryset.filter(user_type=user_type)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = self._base_queryset()
        context['search_query'] = self.request.GET.get('search', '')
        context['user_type_filter'] = self.request.GET.get('user_type', '')
        context['user_types'] = [
            choice for choice in User.UserType.choices
            if choice[0] in MANAGEABLE_USER_TYPES
        ]
        context['analytics_cards'] = [
            {'label': 'Total Users', 'value': users.count(), 'value_class': 'text-gray-900', 'icon': 'group'},
            {'label': 'Active Users', 'value': users.filter(is_active=True).count(), 'value_class': 'text-green-700', 'icon': 'person_check'},
            {'label': 'Inactive Users', 'value': users.filter(is_active=False).count(), 'value_class': 'text-red-700', 'icon': 'person_off'},
        ]
        return context

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

            if self.object.user_type in [
                User.UserType.STAFF,
                User.UserType.LAB_ASSISTANT,
                User.UserType.PHARMACIST,
            ]:
                HospitalStaff.objects.update_or_create(
                    user=self.object,
                    defaults={'hospital': hospital_admin.hospital},
                )

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


class PasswordChangeView(LoginRequiredMixin, FormView):
	"""Dedicated doctor password change page."""
	template_name = 'doctor/password_change.html'
	form_class = PasswordChangeForm
	success_url = reverse_lazy('doctors:doctor_profile')

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
