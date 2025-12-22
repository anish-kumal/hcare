from django.shortcuts import redirect, render
from django.views.generic import CreateView, View
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserRegistrationForm, UserLoginForm
from .models import User


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
    template_name = 'patient/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """
        Redirect to the next URL if available, otherwise to index
        """
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
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
    http_method_names = ['get', 'post', 'options']  # Allow GET requests
    
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)


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
