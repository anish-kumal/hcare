from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.dateparse import parse_date
from auditlog.models import LogEntry
from apps.users.models import User
from apps.doctors.models import Doctor
from apps.patients.models import Patient
from apps.hospitals.models import HospitalAdmin, HospitalStaff


class AuditLogBaseView(LoginRequiredMixin):
    """
    Base mixin for audit log views with role-based access control
    """
    def dispatch(self, request, *args, **kwargs):
        """Check if user is Super Admin or Hospital Admin"""
        user = request.user
        
        # Allow Super Admin
        if user.is_super_admin:
            return super().dispatch(request, *args, **kwargs)
        
        # Allow Hospital Admins (ADMIN role)
        if user.user_type == User.UserType.ADMIN:
            return super().dispatch(request, *args, **kwargs)
        
        # Deny access for other roles
        messages.error(request, "You don't have permission to view audit logs.")
        return redirect('home')  # Change 'home' to your home URL name


class AuditLogListView(AuditLogBaseView, ListView):
    """
    Display audit logs with role-based filtering:
    - Super Admin: sees all audit logs
    - Hospital Admin: sees only logs for their hospital's users
    """
    model = LogEntry
    template_name = 'logs/auditlog_list.html'
    context_object_name = 'logs'
    paginate_by = 10

    def _apply_filters(self, queryset):
        """Apply search and action filters from query parameters."""
        search_query = (self.request.GET.get('search') or '').strip()
        action = (self.request.GET.get('action') or '').strip()
        timestamp_date = (self.request.GET.get('timestamp_date') or '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(actor__username__icontains=search_query)
                | Q(actor__first_name__icontains=search_query)
                | Q(actor__last_name__icontains=search_query)
                | Q(object_repr__icontains=search_query)
                | Q(content_type__model__icontains=search_query)
            )

        if action in {'0', '1', '2'}:
            queryset = queryset.filter(action=int(action))

        if timestamp_date:
            parsed_date = parse_date(timestamp_date)
            if parsed_date:
                queryset = queryset.filter(timestamp__date=parsed_date)

        return queryset
    
    def get_queryset(self):
        user = self.request.user
        
        # Super Admin sees all logs
        if user.is_super_admin:
            queryset = LogEntry.objects.all().select_related('actor', 'content_type').order_by('-timestamp')
            return self._apply_filters(queryset)
        
        # Hospital Admin sees only logs for their hospital's users
        if user.user_type == User.UserType.ADMIN:
            try:
                hospital_admin = HospitalAdmin.objects.get(user=user)
                hospital = hospital_admin.hospital
                
                # Get all user IDs associated with this hospital
                hospital_user_ids = self._get_hospital_user_ids(hospital)
                
                # Filter logs where actor is one of the hospital's users
                queryset = LogEntry.objects.filter(
                    actor_id__in=hospital_user_ids
                ).select_related('actor', 'content_type').order_by('-timestamp')
                return self._apply_filters(queryset)
            except HospitalAdmin.DoesNotExist:
                return LogEntry.objects.none()
        
        return LogEntry.objects.none()
    
    def _get_hospital_user_ids(self, hospital):
        """
        Get all user IDs associated with a hospital:
        - Doctors
        - Hospital Staff (including Lab Assistants, Pharmacists)
        - Hospital Admins
        - Patients registered at this hospital
        - Patients with appointments at this hospital
        """
        user_ids = set()
        
        # Get doctors
        doctors = Doctor.objects.filter(hospital=hospital)
        user_ids.update(doctors.values_list('user_id', flat=True))
        
        # Get hospital staff (admin, staff, lab assistant, pharmacist)
        staff = HospitalStaff.objects.filter(hospital=hospital)
        user_ids.update(staff.values_list('user_id', flat=True))
        
        # Get hospital admins
        admins = HospitalAdmin.objects.filter(hospital=hospital)
        user_ids.update(admins.values_list('user_id', flat=True))
        
        # Get patients registered at this hospital
        patients = Patient.objects.filter(hospital=hospital)
        user_ids.update(patients.values_list('user_id', flat=True))
        
        # Get patients with appointments at this hospital
        appointment_patients = Patient.objects.filter(
            appointments__hospital=hospital
        ).distinct()
        user_ids.update(appointment_patients.values_list('user_id', flat=True))
        
        return list(user_ids)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        logs = self.get_queryset()

        # Preserve active filters in template controls
        context['search_query'] = (self.request.GET.get('search') or '').strip()
        context['action_filter'] = (self.request.GET.get('action') or '').strip()
        context['timestamp_date_filter'] = (self.request.GET.get('timestamp_date') or '').strip()
        context['analytics_cards'] = [
            {'label': 'Total Logs', 'value': logs.count(), 'icon': 'history'},
            {'label': 'Create Actions', 'value': logs.filter(action=0).count(), 'icon': 'add_circle'},
            {'label': 'Update Actions', 'value': logs.filter(action=1).count(), 'icon': 'edit'},
            {'label': 'Delete Actions', 'value': logs.filter(action=2).count(), 'icon': 'delete'},
        ]
        
        # Add info about whose logs are being viewed
        if user.is_super_admin:
            context['viewing_scope'] = 'All Users (Super Admin)'
        elif user.user_type == User.UserType.ADMIN:
            try:
                hospital_admin = HospitalAdmin.objects.get(user=user)
                context['hospital'] = hospital_admin.hospital
                context['viewing_scope'] = f"{hospital_admin.hospital.name} Users"
            except HospitalAdmin.DoesNotExist:
                context['viewing_scope'] = 'No Hospital Access'
        
        return context


class AuditLogDetailView(AuditLogBaseView, DetailView):
    """
    Display detailed view of a single audit log entry
    """
    model = LogEntry
    template_name = 'logs/auditlog_detail.html'
    context_object_name = 'log'
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_super_admin:
            return LogEntry.objects.select_related('actor', 'content_type')
        
        if user.user_type == User.UserType.ADMIN:
            try:
                hospital_admin = HospitalAdmin.objects.get(user=user)
                hospital = hospital_admin.hospital
                hospital_user_ids = self._get_hospital_user_ids(hospital)
                
                return LogEntry.objects.filter(
                    actor_id__in=hospital_user_ids
                ).select_related('actor', 'content_type')
            except HospitalAdmin.DoesNotExist:
                return LogEntry.objects.none()
        
        return LogEntry.objects.none()
    
    def _get_hospital_user_ids(self, hospital):
        """Helper method - same as in AuditLogListView"""
        user_ids = set()
        
        doctors = Doctor.objects.filter(hospital=hospital)
        user_ids.update(doctors.values_list('user_id', flat=True))
        
        staff = HospitalStaff.objects.filter(hospital=hospital)
        user_ids.update(staff.values_list('user_id', flat=True))
        
        admins = HospitalAdmin.objects.filter(hospital=hospital)
        user_ids.update(admins.values_list('user_id', flat=True))
        
        patients = Patient.objects.filter(hospital=hospital)
        user_ids.update(patients.values_list('user_id', flat=True))
        
        # Get patients with appointments at this hospital
        appointment_patients = Patient.objects.filter(
            appointments__hospital=hospital
        ).distinct()
        user_ids.update(appointment_patients.values_list('user_id', flat=True))
        
        return list(user_ids)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        log = self.object
        
        # Parse changes if available
        if hasattr(log, 'changes') and log.changes:
            context['changes_list'] = log.changes
        
        return context
