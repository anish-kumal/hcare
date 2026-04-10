

from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Hospital, HospitalAdmin, HospitalDepartment
from .forms import HospitalForm, HospitalAdminForm, HospitalDepartmentForm, KhaltiSetupForm
from apps.base.mixin import SuperAdminOnlyMixin


class HospitalListView(SuperAdminOnlyMixin, ListView):
    """List all hospitals"""
    model = Hospital
    template_name = 'hospitals/hospital_list.html'
    context_object_name = 'hospitals'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Hospital.objects.all().order_by('-created')
        
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(registration_number__icontains=search_query)
            )
        
        # Filter by verification status
        is_verified = self.request.GET.get('is_verified', '')
        if is_verified == 'true':
            queryset = queryset.filter(is_verified=True)
        elif is_verified == 'false':
            queryset = queryset.filter(is_verified=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospitals = Hospital.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['is_verified_filter'] = self.request.GET.get('is_verified', '')
        context['analytics_cards'] = [
            {'label': 'Total Hospitals', 'value': hospitals.count(), 'value_class': 'text-gray-900'},
            {'label': 'Verified', 'value': hospitals.filter(is_verified=True).count(), 'value_class': 'text-green-700'},
            {'label': 'Unverified', 'value': hospitals.filter(is_verified=False).count(), 'value_class': 'text-amber-700'},
        ]
        return context


class HospitalDetailView(SuperAdminOnlyMixin, DetailView):
    """View hospital details"""
    model = Hospital
    template_name = 'hospitals/hospital_detail.html'
    context_object_name = 'hospital'
    slug_field = 'id'
    slug_url_kwarg = 'pk'


class HospitalCreateView(SuperAdminOnlyMixin, CreateView):
    """Create a new hospital"""
    model = Hospital
    form_class = HospitalForm
    template_name = 'hospitals/hospital_form.html'
    success_url = reverse_lazy('hospitals:hospital_list')
    
    def form_valid(self, form):
        if form.cleaned_data.get('is_verified'):
            form.instance.verified_by = self.request.user
            form.instance.verified_at = timezone.now()
        messages.success(self.request, 'Hospital created successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class HospitalUpdateView(SuperAdminOnlyMixin, UpdateView):
    """Update hospital information"""
    model = Hospital
    form_class = HospitalForm
    template_name = 'hospitals/hospital_form.html'
    success_url = reverse_lazy('hospitals:hospital_list')
    slug_field = 'id'
    slug_url_kwarg = 'pk'
    
    def form_valid(self, form):
        if form.cleaned_data.get('is_verified'):
            if not self.object.verified_at:
                form.instance.verified_at = timezone.now()
            if not self.object.verified_by:
                form.instance.verified_by = self.request.user
        else:
            form.instance.verified_at = None
            form.instance.verified_by = None
        messages.success(self.request, 'Hospital updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class HospitalDeleteView(SuperAdminOnlyMixin, DeleteView):
    """Delete a hospital"""
    model = Hospital
    template_name = 'partials/delete.html'
    success_url = reverse_lazy('hospitals:hospital_list')
    slug_field = 'id'
    slug_url_kwarg = 'pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'delete_page_title': 'Delete Hospital - Health Care',
            'delete_confirm_title': f'Delete {self.object.name}?',
            'delete_confirm_message': (
                f'Are you sure you want to delete {self.object.name}? '
                'This action cannot be undone.'
            ),
            'delete_warning_text': (
                'Deleting this hospital will permanently remove all related records.'
            ),
            'delete_button_label': 'Delete Hospital',
            'cancel_url': reverse_lazy('hospitals:hospital_list'),
        })
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Hospital deleted successfully!')
        return super().delete(request, *args, **kwargs)


class HospitalAdminListView(SuperAdminOnlyMixin, ListView):
    """List all admins for a specific hospital"""
    model = HospitalAdmin
    template_name = 'hospitals/hospital_admin_list.html'
    context_object_name = 'admins'
    paginate_by = 10
    
    def get_queryset(self):
        hospital_id = self.kwargs.get('hospital_id')
        return HospitalAdmin.objects.filter(hospital_id=hospital_id).order_by('-created')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital_id = self.kwargs.get('hospital_id')
        context['hospital'] = get_object_or_404(Hospital, id=hospital_id)
        return context


class HospitalAdminCreateView(SuperAdminOnlyMixin, CreateView):
    """Add a new admin to a hospital"""
    model = HospitalAdmin
    form_class = HospitalAdminForm
    template_name = 'hospitals/hospital_admin_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital_id = self.kwargs.get('hospital_id')
        context['hospital'] = get_object_or_404(Hospital, id=hospital_id)
        return context
    
    def form_valid(self, form):
        hospital_id = self.kwargs.get('hospital_id')
        hospital = get_object_or_404(Hospital, id=hospital_id)
        form.instance.hospital = hospital

        password = form.cleaned_data.get('password')
        response = super().form_valid(form)

        if password:
            admin_user = self.object.user
            login_url = self.request.build_absolute_uri(reverse_lazy('users:administer_login'))
            context = {
                'title': 'Your hospital admin account for',
                'user_name': admin_user.get_full_name() or admin_user.username,
                'hospital_name': hospital.name,
                'username': admin_user.username,
                'password': password,
                'login_url': login_url,
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }

            try:
                html_message = render_to_string('email/credentials_email.html', context)
                plain_message = strip_tags(html_message)
                send_mail(
                    subject='Your Hospital Admin Login Credentials',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin_user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                messages.success(self.request, 'Admin added to hospital successfully! Credentials email sent.')
            except Exception:
                messages.warning(
                    self.request,
                    'Admin added successfully, but credential email could not be sent. Please share credentials manually.'
                )
        else:
            messages.success(self.request, 'Admin added to hospital successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def get_success_url(self):
        hospital_id = self.kwargs.get('hospital_id')
        return reverse_lazy('hospitals:hospital_admin_list', kwargs={'hospital_id': hospital_id})


class HospitalAdminUpdateView(SuperAdminOnlyMixin, UpdateView):
    """Update hospital admin information"""
    model = HospitalAdmin
    form_class = HospitalAdminForm
    template_name = 'hospitals/hospital_admin_form.html'
    slug_field = 'id'
    slug_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hospital'] = self.object.hospital
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Admin information updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('hospitals:hospital_admin_list', kwargs={'hospital_id': self.object.hospital.id})

class HospitalAdminDetailView(SuperAdminOnlyMixin, DetailView):
    """View hospital admin details"""
    model = HospitalAdmin
    template_name = 'hospitals/hospital_admin_detail.html'
    context_object_name = 'admin'
    slug_field = 'id'
    slug_url_kwarg = 'pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hospital'] = self.object.hospital
        return context
    

class HospitalAdminDeleteView(SuperAdminOnlyMixin, DeleteView):
    """Remove an admin from a hospital"""
    model = HospitalAdmin
    template_name = 'partials/delete.html'
    slug_field = 'id'
    slug_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        full_name = self.object.user.get_full_name() or self.object.user.email
        context['hospital'] = self.object.hospital
        context.update({
            'delete_page_title': 'Remove Hospital Admin - Health Care',
            'delete_confirm_title': f'Remove {full_name}?',
            'delete_confirm_message': (
                f'Are you sure you want to remove {full_name} from '
                f'{self.object.hospital.name}?'
            ),
            'delete_warning_text': (
                'This will revoke this admin account\'s access to the hospital.'
            ),
            'delete_button_label': 'Remove Admin',
            'cancel_url': reverse_lazy(
                'hospitals:hospital_admin_list',
                kwargs={'hospital_id': self.object.hospital.id},
            ),
        })
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Admin removed from hospital successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse_lazy('hospitals:hospital_admin_list', kwargs={'hospital_id': self.object.hospital.id})


# Hospital Admin Views (for admins to manage their own hospital)
class HospitalAdminOnlyMixin(LoginRequiredMixin):
    """Mixin to restrict access to hospital admins only"""
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not request.user.is_admin:
            raise PermissionDenied("You don't have permission to access this page.")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_hospital(self):
        """Get the hospital for the current admin user"""
        try:
            hospital_admin = HospitalAdmin.objects.get(user=self.request.user)
            return hospital_admin.hospital
        except HospitalAdmin.DoesNotExist:
            raise PermissionDenied("You are not assigned to any hospital.")


class AdminOwnHospitalDetailView(HospitalAdminOnlyMixin, DetailView):
    """View hospital details (for hospital admin of that hospital)"""
    model = Hospital
    template_name = 'hospitals/hospital_detail.html'
    context_object_name = 'hospital'
    
    def get_object(self):
        return self.get_hospital()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_hospital_admin'] = True
        return context


class AdminOwnHospitalUpdateView(HospitalAdminOnlyMixin, UpdateView):
    """Update hospital details (for hospital admin of that hospital)"""
    model = Hospital
    form_class = HospitalForm
    template_name = 'hospitals/hospital_form.html'
    
    def get_object(self):
        return self.get_hospital()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit {self.object.name}'
        context['action'] = 'update'
        context['is_hospital_admin'] = True
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Hospital details updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('hospitals:admin_hospital_detail')

class HospitalDepartmentListView(HospitalAdminOnlyMixin, ListView):
    """List all departments for the hospital admin's hospital"""
    model = HospitalDepartment
    template_name = 'hospitals/hospital_department_list.html'
    context_object_name = 'departments'
    paginate_by = 10
    
    def get_queryset(self):
        hospital = self.get_hospital()
        return hospital.departments.all().order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hospital'] = self.get_hospital()
        return context
    
class HospitalDepartmentCreateView(HospitalAdminOnlyMixin, CreateView):
    """Add a new department to the hospital admin's hospital"""
    model = HospitalDepartment
    form_class = HospitalDepartmentForm
    template_name = 'hospitals/hospital_department_form.html'
    
    def form_valid(self, form):
        form.instance.hospital = self.get_hospital()
        messages.success(self.request, 'Department added successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('hospitals:hospital_department_list')
    
class HospitalDepartmentUpdateView(HospitalAdminOnlyMixin, UpdateView):
    """Update a department in the hospital admin's hospital"""
    model = HospitalDepartment
    form_class = HospitalDepartmentForm
    template_name = 'hospitals/hospital_department_form.html'
    
    def get_queryset(self):
        hospital = self.get_hospital()
        return hospital.departments.all()
    
    def form_valid(self, form):
        messages.success(self.request, 'Department updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('hospitals:hospital_department_list')

class HospitalDepartmentDeleteView(HospitalAdminOnlyMixin, DeleteView):
    """Delete a department from the hospital admin's hospital"""
    model = HospitalDepartment
    template_name = 'partials/delete.html'
    success_url = reverse_lazy('hospitals:hospital_department_list')
    
    def get_queryset(self):
        hospital = self.get_hospital()
        return hospital.departments.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'delete_page_title': 'Delete Department - Health Care',
            'delete_confirm_title': f'Delete {self.object.name}?',
            'delete_confirm_message': (
                f'Are you sure you want to delete the {self.object.name} '
                f'department? This action cannot be undone.'
            ),
            'delete_warning_text': (
                'Deleting this department will permanently remove all related records.'
            ),
            'delete_button_label': 'Delete Department',
            'cancel_url': reverse_lazy('hospitals:hospital_department_list'),
        })
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Department deleted successfully!')
        return super().delete(request, *args, **kwargs)


class HospitalRegistartionView(CreateView):
    """Hospital registration view for new hospitals to sign up"""
    model = Hospital
    form_class = HospitalForm
    template_name = 'hospitals/hospital_registration.html'
    success_url = reverse_lazy('administer')
    
    def form_valid(self, form):
        # Ensure public signups start as pending and inactive for admin review.
        form.instance.is_verified = False
        form.instance.is_active = False

        messages.success(
            self.request,
            'Registration successful! Your hospital will be reviewed and verified by our team shortly. A yearly fee of NRs 10,000 applies for listing approval.'
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class KhaltiSetupView(LoginRequiredMixin, FormView):
    """
    View for hospital admins to set up Khalti payment keys.
    Only shows khalti_secret_key and khalti_public_key fields.
    This is displayed when the admin first logs in if keys are empty.
    """
    form_class = KhaltiSetupForm
    template_name = 'hospitals/khalti_setup.html'
    login_url = reverse_lazy('users:administer_login')
    
    def get_object(self):
        """Get the hospital associated with the admin"""
        if hasattr(self.request.user, 'hospital_admin_profile'):
            return self.request.user.hospital_admin_profile.hospital
        raise PermissionDenied("You are not a hospital admin.")
    
    def get_context_data(self, **kwargs):
        """Add hospital info to context"""
        context = super().get_context_data(**kwargs)
        hospital = self.get_object()
        context['hospital'] = hospital
        context['page_title'] = f'Khalti Payment Setup - {hospital.name}'
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_object()
        return kwargs
    
    def form_valid(self, form):
        """Save khalti keys to the hospital"""
        form.save()
        
        messages.success(
            self.request,
            'Khalti payment keys have been set up successfully! You can now proceed.'
        )
        
        # Redirect to admin dashboard or next page
        next_url = self.request.GET.get('next', reverse_lazy('admin_dashboard'))
        return redirect(next_url)
    
    def form_invalid(self, form):
        """Show form errors"""
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)