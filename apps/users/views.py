from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import CreateView, View, ListView, DetailView, UpdateView, DeleteView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import logout
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserRegistrationForm, UserLoginForm, UserManagementForm
from .models import User
from apps.hospitals.models import HospitalAdmin
from apps.base.mixin import SuperAdminOnlyMixin

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

class HospitalAdminUserListView( ListView):
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


class HospitalAdminUserCreateView( CreateView):
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


class HospitalAdminUserDetailView( DetailView):
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


class HospitalAdminUserUpdateView( UpdateView):
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


class HospitalAdminUserDeleteView( DeleteView):
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
