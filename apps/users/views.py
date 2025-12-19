from django.shortcuts import redirect
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserRegistrationForm, UserLoginForm


class UserRegisterView(CreateView):
    """
    Class-based view for user registration
    """
    form_class = UserRegistrationForm
    template_name = 'register.html'
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
    template_name = 'login.html'
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
