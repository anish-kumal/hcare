from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Hospital, HospitalAdmin
from .forms import HospitalForm, HospitalAdminForm
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
        context['search_query'] = self.request.GET.get('search', '')
        context['is_verified_filter'] = self.request.GET.get('is_verified', '')
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
        messages.success(self.request, 'Admin added to hospital successfully!')
        return super().form_valid(form)
    
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

