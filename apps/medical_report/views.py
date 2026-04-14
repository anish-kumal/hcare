from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views import View
from django.http import Http404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils.dateparse import parse_date
from apps.medical_report.models import MedicalReport
from apps.medical_report.forms import (
    AdminMedicalReportForm,
    PatientMedicalReportShareForm,
)
from apps.base.mixin import SuperAdminAndAdminOnlyMixin, AdminHospitalScopedQuerysetMixin, AdminLabAssistantOnlyMixin
from apps.appointments.views import PatientAccessMixin
from apps.patients.models import PatientAppointment
from django.urls import reverse_lazy
from django.shortcuts import redirect


class MedicalReportPreviewContextMixin:
    """Provide preview context for report image."""

    def build_preview_context(self, report):
        preview_image_url = report.get_report_file_url() if report.report_file else ''

        return {
            'preview_image_url': preview_image_url,
            'preview_total_pages': 1 if preview_image_url else 0,
            'preview_current_page': 1,
            'preview_has_previous': False,
            'preview_has_next': False,
            'preview_previous_page_number': None,
            'preview_next_page_number': None,
        }


class DoctorOnlyMixin(LoginRequiredMixin):
    """Restrict views to doctor users only."""
    login_url = 'users:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_doctor:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)


def get_request_user_hospital_name(user):
    """Return current request user's associated hospital name when available."""
    if not user or not user.is_authenticated:
        return ''

    try:
        if hasattr(user, 'hospital_admin_profile'):
            return user.hospital_admin_profile.hospital.name
        if hasattr(user, 'doctor_profile'):
            return user.doctor_profile.hospital.name
        if hasattr(user, 'hospital_staff_profile'):
            return user.hospital_staff_profile.hospital.name
    except Exception:
        return ''

    return ''


class DoctorPatientScopedReportMixin(DoctorOnlyMixin):
    """Scope reports to patients that belong to current doctor's appointments."""

    def get_doctor_patient_ids(self):
        return PatientAppointment.objects.filter(
            doctor__user=self.request.user,
        ).values_list('patient_id', flat=True).distinct()

    def get_doctor_patient_queryset(self):
        patient_ids = self.get_doctor_patient_ids()
        return MedicalReport.objects.filter(patient_id__in=patient_ids)


class DoctorMedicalReportListView(DoctorPatientScopedReportMixin, ListView):
    """Doctor view to list medical reports for own appointment patients."""
    model = MedicalReport
    template_name = 'doctors/medical_report_list.html'
    context_object_name = 'medical_reports'
    paginate_by = 10

    def get_queryset(self):
        return self.get_doctor_patient_queryset().select_related(
            'patient__user',
            'primary_hospital',
            'uploaded_by',
        ).prefetch_related('shared_with').order_by('-created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reports = self.get_doctor_patient_queryset()
        context['analytics_cards'] = [
            {'label': 'Patient Reports', 'value': reports.count(), 'value_class': 'text-gray-900', 'icon': 'description'},
            {
                'label': 'Uploaded By Me',
                'value': reports.filter(uploaded_by=self.request.user).count(),
                'value_class': 'text-blue-700',
                'icon': 'upload_file',
            },
            {
                'label': 'Shared Reports',
                'value': reports.filter(shared_with__isnull=False).distinct().count(),
                'value_class': 'text-emerald-700',
                'icon': 'share',
            },
        ]
        return context


class DoctorMedicalReportDetailView(MedicalReportPreviewContextMixin, DoctorPatientScopedReportMixin, DetailView):
    """Doctor view for report detail limited by doctor-patient ownership."""
    model = MedicalReport
    template_name = 'doctors/medical_report_detail.html'
    context_object_name = 'medical_report'

    def get_queryset(self):
        return self.get_doctor_patient_queryset().select_related(
            'patient__user',
            'primary_hospital',
            'uploaded_by',
        ).prefetch_related('shared_with')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = self.object.uploaded_by_id == self.request.user.id
        context.update(self.build_preview_context(self.object))
        return context


class DoctorMedicalReportCreateView(DoctorPatientScopedReportMixin, CreateView):
    """Doctor can upload reports only for patients tied to doctor's appointments."""
    model = MedicalReport
    form_class = AdminMedicalReportForm
    template_name = 'doctors/medical_report_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        patient_ids = self.get_doctor_patient_ids()
        form.fields['patient'].queryset = form.fields['patient'].queryset.filter(id__in=patient_ids)

        patient_id = self.request.GET.get('patient', '').strip()
        if patient_id.isdigit():
            form.fields['patient'].initial = int(patient_id)

        return form

    def form_valid(self, form):
        patient = form.cleaned_data.get('patient')
        patient_allowed = PatientAppointment.objects.filter(
            doctor__user=self.request.user,
            patient=patient,
        ).exists()

        if not patient_allowed:
            form.add_error('patient', 'You can upload reports only for your own appointment patients.')
            return self.form_invalid(form)

        messages.success(self.request, 'Medical report uploaded successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('medical_report:doctor_medical_report_detail', kwargs={'pk': self.object.pk})


class DoctorMedicalReportUpdateView(DoctorPatientScopedReportMixin, UpdateView):
    """Doctor can edit only reports uploaded by themselves."""
    model = MedicalReport
    form_class = AdminMedicalReportForm
    template_name = 'doctors/medical_report_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return self.get_doctor_patient_queryset().filter(
            uploaded_by=self.request.user,
        ).select_related('patient__user', 'primary_hospital', 'uploaded_by')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        patient_ids = self.get_doctor_patient_ids()
        form.fields['patient'].queryset = form.fields['patient'].queryset.filter(id__in=patient_ids)
        return form

    def form_valid(self, form):
        messages.success(self.request, 'Medical report updated successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('medical_report:doctor_medical_report_detail', kwargs={'pk': self.object.pk})


class AdminMedicalReportCreateView(AdminHospitalScopedQuerysetMixin, AdminLabAssistantOnlyMixin, CreateView):
    """
    Admin view to create a new medical report
    """
    model = MedicalReport
    form_class = AdminMedicalReportForm
    template_name = 'admin/medical_report_form.html'
    success_url = reverse_lazy('medical_report:admin_medical_report_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


    def form_valid(self, form):
        messages.success(self.request, 'Medical report created successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        """Show error messages when form is invalid"""
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field.upper()}: {error}')
        return super().form_invalid(form)

# Admin Views
class AdminMedicalReportListView(AdminHospitalScopedQuerysetMixin, AdminLabAssistantOnlyMixin, ListView):
    """
    Admin view to list all medical reports
    """
    model = MedicalReport
    template_name = 'admin/medical_report_list.html'
    context_object_name = 'medical_reports'
    paginate_by = 10

    def get_queryset(self):
        queryset = MedicalReport.objects.select_related(
            'patient__user',
            'primary_hospital',
            'uploaded_by',
        ).all()
        queryset = self.scope_queryset_for_admin(queryset, hospital_field='primary_hospital_id')

        search_query = (self.request.GET.get('search') or '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(patient__user__first_name__icontains=search_query)
                | Q(patient__user__last_name__icontains=search_query)
                | Q(primary_hospital__name__icontains=search_query)
                | Q(report_name__icontains=search_query)
                | Q(uploaded_by__first_name__icontains=search_query)
                | Q(uploaded_by__last_name__icontains=search_query)
                | Q(uploaded_by__username__icontains=search_query)
            )

        created_date = (self.request.GET.get('created_date') or '').strip()
        if created_date:
            parsed_date = parse_date(created_date)
            if parsed_date:
                queryset = queryset.filter(created__date=parsed_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reports = self.scope_queryset_for_admin(MedicalReport.objects.all(), hospital_field='primary_hospital_id')
        context['search_query'] = (self.request.GET.get('search') or '').strip()
        context['created_date_filter'] = (self.request.GET.get('created_date') or '').strip()
        context['analytics_cards'] = [
            {'label': 'Total Reports', 'value': reports.count(), 'value_class': 'text-gray-900', 'icon': 'description'},
            {'label': 'Shared Reports', 'value': reports.filter(shared_with__isnull=False).distinct().count(), 'value_class': 'text-blue-700', 'icon': 'share'},
            {'label': 'Private Reports', 'value': reports.filter(shared_with__isnull=True).count(), 'value_class': 'text-amber-700', 'icon': 'lock'},
        ]
        return context


class AdminMedicalReportDetailView(MedicalReportPreviewContextMixin, AdminHospitalScopedQuerysetMixin, AdminLabAssistantOnlyMixin, DetailView):
    """
    Admin view to show medical report details
    """
    model = MedicalReport
    template_name = 'admin/medical_report_detail.html'
    context_object_name = 'medical_report'

    def get_queryset(self):
        queryset = MedicalReport.objects.select_related('patient', 'primary_hospital', 'uploaded_by').all()
        return self.scope_queryset_for_admin(queryset, hospital_field='primary_hospital_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.build_preview_context(self.object))
        return context


class AdminMedicalReportUpdateView(AdminHospitalScopedQuerysetMixin, AdminLabAssistantOnlyMixin, UpdateView):
    """
    Admin view to update medical report and manage sharing
    """
    model = MedicalReport
    form_class = AdminMedicalReportForm
    template_name = 'admin/medical_report_form.html'
    success_url = reverse_lazy('medical_report:admin_medical_report_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        queryset = MedicalReport.objects.select_related('patient', 'primary_hospital', 'uploaded_by').all()
        return self.scope_queryset_for_admin(queryset, hospital_field='primary_hospital_id')

    def form_valid(self, form):
        messages.success(self.request, 'Medical report updated successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        """Show error messages when form is invalid"""
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field.upper()}: {error}')
        return super().form_invalid(form)


class AdminMedicalReportDeleteView(AdminHospitalScopedQuerysetMixin, AdminLabAssistantOnlyMixin, DeleteView):
    """
    Admin view to delete medical report
    """
    model = MedicalReport
    template_name = 'admin/medical_report_confirm_delete.html'
    success_url = reverse_lazy('medical_report:admin_medical_report_list')

    def get_queryset(self):
        queryset = MedicalReport.objects.select_related('patient', 'primary_hospital', 'uploaded_by').all()
        return self.scope_queryset_for_admin(queryset, hospital_field='primary_hospital_id')

    def form_valid(self, form):
        """Show success message when report is deleted"""
        response = super().form_valid(form)
        messages.success(self.request, 'Medical report deleted successfully!')
        return response


class PatientMedicalReportDetailView(MedicalReportPreviewContextMixin, PatientAccessMixin, DetailView):
    """Patient-facing medical report details for the report owner only."""
    model = MedicalReport
    template_name = 'patients/medical_report_detail.html'
    context_object_name = 'medical_report'

    def get_queryset(self):
        return MedicalReport.objects.filter(
            patient__user=self.request.user,
        ).select_related(
            'patient__user',
            'primary_hospital',
            'uploaded_by',
        ).prefetch_related('shared_with')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.build_preview_context(self.object))
        return context


class PatientMedicalReportUpdateView(PatientAccessMixin, UpdateView):
    """Patient can update only sharing for their own report."""

    model = MedicalReport
    form_class = PatientMedicalReportShareForm
    template_name = 'patients/medical_report_edit.html'
    context_object_name = 'medical_report'

    def get_queryset(self):
        return MedicalReport.objects.filter(
            patient__user=self.request.user,
        ).select_related(
            'patient__user',
            'primary_hospital',
            'uploaded_by',
        ).prefetch_related('shared_with')

    def get_success_url(self):
        return reverse_lazy('medical_report:patient_medical_report_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Report sharing updated successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Could not update sharing. Please check your selection.')
        return super().form_invalid(form)


class MedicalReportDownloadMixin:
    """Redirect report requests to storage-backed URLs."""

    def _require_report_file(self, report):
        if not report.report_file:
            raise Http404('Report file not available.')
        return report

    def _download_response(self, report):
        report = self._require_report_file(report)
        return redirect(report.get_report_download_url())

    def _view_response(self, report):
        report = self._require_report_file(report)
        return redirect(report.get_report_file_url())


class PatientMedicalReportDownloadView(PatientAccessMixin, MedicalReportDownloadMixin, View):
    """Allow patient to download only their own medical report."""

    def get(self, request, pk, *args, **kwargs):
        report = MedicalReport.objects.filter(
            pk=pk,
            patient__user=request.user,
        ).first()
        if not report:
            raise Http404('Medical report not found.')
        return self._download_response(report)


class PatientMedicalReportViewFileView(PatientAccessMixin, MedicalReportDownloadMixin, View):
    """Allow patient to open (inline) only their own medical report file."""

    def get(self, request, pk, *args, **kwargs):
        report = MedicalReport.objects.filter(
            pk=pk,
            patient__user=request.user,
        ).first()
        if not report:
            raise Http404('Medical report not found.')
        return self._view_response(report)


class AdminMedicalReportDownloadView(AdminHospitalScopedQuerysetMixin, SuperAdminAndAdminOnlyMixin, MedicalReportDownloadMixin, View):
    """Allow admin/super-admin to download medical reports from detail pages."""

    def get(self, request, pk, *args, **kwargs):
        report = self.scope_queryset_for_admin(MedicalReport.objects.filter(pk=pk), hospital_field='primary_hospital_id').first()
        if not report:
            raise Http404('Medical report not found.')
        return self._download_response(report)


class AdminMedicalReportViewFileView(AdminHospitalScopedQuerysetMixin, SuperAdminAndAdminOnlyMixin, MedicalReportDownloadMixin, View):
    """Allow admin/super-admin to open report files inline from detail pages."""

    def get(self, request, pk, *args, **kwargs):
        report = self.scope_queryset_for_admin(MedicalReport.objects.filter(pk=pk), hospital_field='primary_hospital_id').first()
        if not report:
            raise Http404('Medical report not found.')
        return self._view_response(report)


class DoctorMedicalReportDownloadView(DoctorPatientScopedReportMixin, MedicalReportDownloadMixin, View):
    """Allow doctors to download reports for their appointment patients."""

    def get(self, request, pk, *args, **kwargs):
        report = self.get_doctor_patient_queryset().filter(pk=pk).first()
        if not report:
            raise Http404('Medical report not found.')
        return self._download_response(report)


class DoctorMedicalReportViewFileView(DoctorPatientScopedReportMixin, MedicalReportDownloadMixin, View):
    """Allow doctors to open report files inline for their appointment patients."""

    def get(self, request, pk, *args, **kwargs):
        report = self.get_doctor_patient_queryset().filter(pk=pk).first()
        if not report:
            raise Http404('Medical report not found.')
        return self._view_response(report)
