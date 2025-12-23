from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import CreateView, View, ListView, DetailView, UpdateView, DeleteView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserRegistrationForm, UserLoginForm, UserManagementForm
from .models import User
from apps.hospitals.models import HospitalAdmin


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
        """
        Redirect to the appropriate dashboard based on user role
        """
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        
        user = self.request.user
        
        # Redirect based on user type/role
        if user.is_super_admin:
            return reverse_lazy('super_admin_dashboard')
        elif user.is_admin:
            return reverse_lazy('admin_dashboard')
        elif user.is_doctor:
            return reverse_lazy('doctor_dashboard')
        elif user.is_lab_assistant:
            return reverse_lazy('lab_assistant_dashboard')
        elif user.is_patient:
            return reverse_lazy('patient_dashboard')
        else:
            # Default redirect for other roles (staff, pharmacist, etc.)
            return reverse_lazy('index')
    
    def form_valid(self, form):
        """
        If the form is valid, log the user in and display success message
        """
        messages.success(
            self.request,
            f'Welcome back, {form.get_user().get_full_name() or form.get_user().username}!'
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


class UserLogoutView(LoginRequiredMixin, LogoutView):
    """
    Class-based view for user logout
    """
    next_page = reverse_lazy('index')  # Redirect to home after logout
    http_method_names = ['get', 'post']  # Allow both GET and POST
    
    def get(self, request, *args, **kwargs):
        messages.success(request, 'You have been logged out successfully.')
        return self.post(request, *args, **kwargs)


class PasswordResetView(View):
    """
    Class-based view for password reset after OTP verification
    """
    template_name = 'patient/password_reset.html'
    
    def get(self, request, user_id=None):
        """Display password reset form"""
        context = {'user_id': user_id}
        return render(request, self.template_name, context)
    
    def post(self, request, user_id=None):
        """Handle password reset"""
        password1 = request.POST.get('password1', '').strip()
        password2 = request.POST.get('password2', '').strip()
        
        if not password1 or not password2:
            messages.error(request, "Both password fields are required.")
            return render(request, self.template_name, {'user_id': user_id})
        
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, self.template_name, {'user_id': user_id})
        
        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, self.template_name, {'user_id': user_id})
        
        try:
            user = User.objects.get(id=user_id)
            user.set_password(password1)
            user.save()
            messages.success(request, "Password reset successfully! Please log in with your new password.")
            return redirect('users:login')
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('users:login')


# User Management Views for Super Admin and Hospital Admin

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


class HospitalAdminOnlyMixin(LoginRequiredMixin):
    """Mixin to restrict access to hospital admins"""
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        # Check if user is hospital admin
        try:
            HospitalAdmin.objects.get(user=request.user)
        except HospitalAdmin.DoesNotExist:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)


# Super Admin User Management Views

class AdminUserListView(SuperAdminOnlyMixin, ListView):
    """List all users for Super Admin"""
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-created')
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
        
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['user_type_filter'] = self.request.GET.get('user_type', '')
        context['user_types'] = User.UserType.choices
        return context


class AdminUserDetailView(SuperAdminOnlyMixin, DetailView):
    """View user details for Super Admin"""
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'user_obj'
    slug_field = 'id'
    slug_url_kwarg = 'pk'


class AdminUserCreateView(SuperAdminOnlyMixin, CreateView):
    """Create new user for Super Admin"""
    model = User
    form_class = UserManagementForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:admin_user_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'User created successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New User'
        context['action'] = 'create'
        return context


class AdminUserUpdateView(SuperAdminOnlyMixin, UpdateView):
    """Update user for Super Admin"""
    model = User
    form_class = UserManagementForm
    template_name = 'users/user_form.html'
    slug_field = 'id'
    slug_url_kwarg = 'pk'
    success_url = reverse_lazy('users:admin_user_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'User updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit User - {self.object.get_full_name()}'
        context['action'] = 'update'
        return context


class AdminUserDeleteView(SuperAdminOnlyMixin, DeleteView):
    """Delete user for Super Admin"""
    model = User
    template_name = 'users/user_confirm_delete.html'
    slug_field = 'id'
    slug_url_kwarg = 'pk'
    success_url = reverse_lazy('users:admin_user_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'User deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Hospital Admin User Management Views

class HospitalAdminUserListView(HospitalAdminOnlyMixin, ListView):
    """List users for a Hospital Admin (only their hospital users)"""
    model = User
    template_name = 'users/hospital_user_list.html'
    context_object_name = 'users'
    paginate_by = 15
    
    def get_queryset(self):
        # Get hospital admin's hospital
        hospital_admin = HospitalAdmin.objects.get(user=self.request.user)
        hospital = hospital_admin.hospital
        
        # Get all hospital admins for this hospital
        hospital_admins = HospitalAdmin.objects.filter(hospital=hospital).values_list('user_id', flat=True)
        
        queryset = User.objects.filter(id__in=hospital_admins).order_by('-created')
        search_query = self.request.GET.get('search', '')
        
        if search_query:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital_admin = HospitalAdmin.objects.get(user=self.request.user)
        context['hospital'] = hospital_admin.hospital
        context['search_query'] = self.request.GET.get('search', '')
        return context


class HospitalAdminUserCreateView(HospitalAdminOnlyMixin, CreateView):
    """Create new user for Hospital Admin (only for their hospital)"""
    model = User
    form_class = UserManagementForm
    template_name = 'users/hospital_user_form.html'
    
    def form_valid(self, form):
        # Get hospital for this hospital admin
        hospital_admin = HospitalAdmin.objects.get(user=self.request.user)
        
        # Save the user
        response = super().form_valid(form)
        
        # Create HospitalAdmin entry for the new user
        HospitalAdmin.objects.create(
            user=form.instance,
            hospital=hospital_admin.hospital
        )
        
        messages.success(self.request, f'{form.instance.get_full_name} has been added to {hospital_admin.hospital.name}!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('users:hospital_user_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital_admin = HospitalAdmin.objects.get(user=self.request.user)
        context['hospital'] = hospital_admin.hospital
        context['action'] = 'create'
        return context


class HospitalAdminUserDetailView(HospitalAdminOnlyMixin, DetailView):
    """View user details for Hospital Admin (only their hospital users)"""
    model = User
    template_name = 'users/hospital_user_detail.html'
    context_object_name = 'user_obj'
    slug_field = 'id'
    slug_url_kwarg = 'pk'
    
    def get_queryset(self):
        hospital_admin = HospitalAdmin.objects.get(user=self.request.user)
        hospital = hospital_admin.hospital
        hospital_admins = HospitalAdmin.objects.filter(hospital=hospital).values_list('user_id', flat=True)
        return User.objects.filter(id__in=hospital_admins)
    
    def get_object(self):
        try:
            return super().get_object()
        except User.DoesNotExist:
            messages.error(self.request, 'User not found or you do not have access.')
            return redirect('users:hospital_user_list')


class HospitalAdminUserUpdateView(HospitalAdminOnlyMixin, UpdateView):
    """Update user for Hospital Admin (only their hospital users)"""
    model = User
    form_class = UserManagementForm
    template_name = 'users/hospital_user_form.html'
    slug_field = 'id'
    slug_url_kwarg = 'pk'
    
    def get_queryset(self):
        hospital_admin = HospitalAdmin.objects.get(user=self.request.user)
        hospital = hospital_admin.hospital
        hospital_admins = HospitalAdmin.objects.filter(hospital=hospital).values_list('user_id', flat=True)
        return User.objects.filter(id__in=hospital_admins)
    
    def get_success_url(self):
        return reverse_lazy('users:hospital_user_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'User updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def get_object(self):
        try:
            return super().get_object()
        except User.DoesNotExist:
            messages.error(self.request, 'User not found or you do not have access.')
            return redirect('users:hospital_user_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital_admin = HospitalAdmin.objects.get(user=self.request.user)
        context['hospital'] = hospital_admin.hospital
        context['title'] = f'Edit User - {self.object.get_full_name()}'
        context['action'] = 'update'
        return context


class HospitalAdminUserDeleteView(HospitalAdminOnlyMixin, DeleteView):
    """Delete user for Hospital Admin (only their hospital users)"""
    model = User
    template_name = 'users/hospital_user_confirm_delete.html'
    slug_field = 'id'
    slug_url_kwarg = 'pk'
    
    def get_queryset(self):
        hospital_admin = HospitalAdmin.objects.get(user=self.request.user)
        hospital = hospital_admin.hospital
        hospital_admins = HospitalAdmin.objects.filter(hospital=hospital).values_list('user_id', flat=True)
        return User.objects.filter(id__in=hospital_admins)
    
    def get_success_url(self):
        return reverse_lazy('users:hospital_user_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'User deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get_object(self):
        try:
            return super().get_object()
        except User.DoesNotExist:
            messages.error(self.request, 'User not found or you do not have access.')
            return redirect('users:hospital_user_list')
