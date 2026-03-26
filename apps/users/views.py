from django.shortcuts import redirect
from django.views.generic import CreateView, ListView, DetailView, UpdateView, DeleteView, FormView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import PasswordChangeForm, UserRegistrationForm, UserLoginForm, UserManagementForm
from .models import User
from apps.hospitals.models import HospitalAdmin

from apps.base.mixin import SuperAdminAndAdminOnlyMixin, AdminOnlyMixin

class UserRegisterView(CreateView):
    """
    Class-based view for user registration
    """
    form_class = UserRegistrationForm
    template_name = 'patient/register.html'
    success_url = reverse_lazy('users:login')
    
    def dispatch(self, request, *args, **kwargs):
        # Redirect to home if user is already authenticated
        if request.user.is_authenticated:
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """
        If the form is valid, save the user and log them in
        """
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Account created successfully! Please log in.'
        )
        return response
    
    def form_invalid(self, form):
        """
        If the form is invalid, display error messages
        """
        messages.error(
            self.request,
            'There was an error creating your account. Please check the form.'
        )
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
        else:
            return reverse_lazy('index')

    def form_valid(self, form):
        user = form.get_user()
        if user.is_patient:
            logout(self.request)
            messages.error(
                self.request,
                'Unauthorized: This login is for staff only. Patients please use the patient login.'
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



class UserListView(SuperAdminAndAdminOnlyMixin, ListView):
    """List all users for Super Admin"""
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 15
    
    def get_queryset(self):
        manageable_user_types = [
            User.UserType.STAFF,
            User.UserType.LAB_ASSISTANT,
            User.UserType.PHARMACIST,
        ]
        queryset = User.objects.filter(user_type__in=manageable_user_types).order_by('-created')

        if self.request.user.is_admin:
            try:
                hospital_id = self.request.user.hospital_admin_profile.hospital_id
            except HospitalAdmin.DoesNotExist:
                return User.objects.none()
            queryset = queryset.filter(hospital_staff_profile__hospital_id=hospital_id)

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
        
        if user_type in manageable_user_types:
            queryset = queryset.filter(user_type=user_type)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manageable_user_types = [
            User.UserType.STAFF,
            User.UserType.LAB_ASSISTANT,
            User.UserType.PHARMACIST,
        ]
        context['search_query'] = self.request.GET.get('search', '')
        context['user_type_filter'] = self.request.GET.get('user_type', '')
        context['user_types'] = [
            choice for choice in User.UserType.choices
            if choice[0] in manageable_user_types
        ]
        return context

class UserCreateView(AdminOnlyMixin, CreateView):
    """Create user for Super Admin"""
    model = User
    form_class = UserManagementForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'User created successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    
class UserDetailView(SuperAdminAndAdminOnlyMixin, DetailView):
    """View user details for Super Admin"""
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'user_obj'
    slug_field = 'id'
    slug_url_kwarg = 'pk'

    def get_queryset(self):
        return User.objects.filter(
            user_type__in=[
                User.UserType.STAFF,
                User.UserType.LAB_ASSISTANT,
                User.UserType.PHARMACIST,
            ]
        )


class UserUpdateView(SuperAdminAndAdminOnlyMixin, UpdateView):
    """Update user for Super Admin"""
    model = User
    form_class = UserManagementForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user_list')
    slug_field = 'id'
    slug_url_kwarg = 'pk'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'User updated successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)




class UserDeleteView(SuperAdminAndAdminOnlyMixin, DeleteView):
    """Delete user for Super Admin"""
    model = User
    template_name = 'partials/delete.html'
    slug_field = 'id'
    slug_url_kwarg = 'pk'
    success_url = reverse_lazy('users:user_list')

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

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'User deleted successfully!')
        return super().delete(request, *args, **kwargs)


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
