from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views import View
from django.http import Http404, FileResponse
from django.contrib import messages
from pathlib import Path
from django.utils.text import slugify
from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import default_storage
from apps.medical_report.models import MedicalReport
from apps.medical_report.forms import AdminMedicalReportForm, PatientMedicalReportShareForm
from apps.base.mixin import SuperAdminAndAdminOnlyMixin, AdminHospitalScopedQuerysetMixin
from apps.appointments.views import PatientAccessMixin
from django.urls import reverse_lazy

class AdminMedicalReportCreateView(AdminHospitalScopedQuerysetMixin, SuperAdminAndAdminOnlyMixin, CreateView):
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
        """Show success message when report is created"""
        messages.success(self.request, 'Medical report created successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        """Show error messages when form is invalid"""
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field.upper()}: {error}')
        return super().form_invalid(form)

# Admin Views
class AdminMedicalReportListView(AdminHospitalScopedQuerysetMixin, SuperAdminAndAdminOnlyMixin, ListView):
    """
    Admin view to list all medical reports
    """
    model = MedicalReport
    template_name = 'admin/medical_report_list.html'
    context_object_name = 'medical_reports'
    paginate_by = 10

    def get_queryset(self):
        queryset = MedicalReport.objects.select_related('patient', 'primary_hospital', 'uploaded_by').all()
        return self.scope_queryset_for_admin(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reports = self.scope_queryset_for_admin(MedicalReport.objects.all())
        context['analytics_cards'] = [
            {'label': 'Total Reports', 'value': reports.count(), 'value_class': 'text-gray-900', 'icon': 'description'},
            {'label': 'Shared Reports', 'value': reports.filter(shared_with__isnull=False).distinct().count(), 'value_class': 'text-blue-700', 'icon': 'share'},
            {'label': 'Private Reports', 'value': reports.filter(shared_with__isnull=True).count(), 'value_class': 'text-amber-700', 'icon': 'lock'},
        ]
        return context


class AdminMedicalReportDetailView(AdminHospitalScopedQuerysetMixin, SuperAdminAndAdminOnlyMixin, DetailView):
    """
    Admin view to show medical report details
    """
    model = MedicalReport
    template_name = 'admin/medical_report_detail.html'
    context_object_name = 'medical_report'

    def get_queryset(self):
        queryset = MedicalReport.objects.select_related('patient', 'primary_hospital', 'uploaded_by').all()
        return self.scope_queryset_for_admin(queryset)


class AdminMedicalReportUpdateView(AdminHospitalScopedQuerysetMixin, SuperAdminAndAdminOnlyMixin, UpdateView):
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
        return self.scope_queryset_for_admin(queryset)

    def form_valid(self, form):
        """Show success message when report is updated"""
        messages.success(self.request, 'Medical report updated successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        """Show error messages when form is invalid"""
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field.upper()}: {error}')
        return super().form_invalid(form)


class AdminMedicalReportDeleteView(AdminHospitalScopedQuerysetMixin, SuperAdminAndAdminOnlyMixin, DeleteView):
    """
    Admin view to delete medical report
    """
    model = MedicalReport
    template_name = 'admin/medical_report_confirm_delete.html'
    success_url = reverse_lazy('medical_report:admin_medical_report_list')

    def get_queryset(self):
        queryset = MedicalReport.objects.select_related('patient', 'primary_hospital', 'uploaded_by').all()
        return self.scope_queryset_for_admin(queryset)

    def delete(self, request, *args, **kwargs):
        """Show success message when report is deleted"""
        messages.success(request, 'Medical report deleted successfully!')
        return super().delete(request, *args, **kwargs)


class PatientMedicalReportDetailView(PatientAccessMixin, DetailView):
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
    """Stream report files as forced-download attachments."""

    def _build_download_filename(self, report):
        original_name = Path(getattr(report.report_file, 'name', '')).name
        extension = Path(original_name).suffix
        if not extension:
            extension = '.pdf'
        safe_base = slugify(report.report_name) or f'medical-report-{report.pk}'
        return f'{safe_base}{extension}'

    def _legacy_candidates(self, report):
        report_name = Path(getattr(report.report_file, 'name', '')).name
        if not report_name:
            return []
        return [
            Path(settings.BASE_DIR) / report.report_file.name,
            Path(settings.BASE_DIR) / 'medical_reports' / report_name,
            Path(settings.MEDIA_ROOT) / 'medical_reports' / report_name,
        ]

    def _repair_missing_file(self, report):
        """If DB points to a missing file, try known legacy locations and restore it."""
        file_name = getattr(report.report_file, 'name', '')
        if not file_name:
            return False

        for candidate in self._legacy_candidates(report):
            if candidate.exists() and candidate.is_file():
                with candidate.open('rb') as source:
                    default_storage.save(file_name, File(source))
                return True
        return False

    def _open_report_file(self, report):
        if not report.report_file:
            raise Http404('Report file not available.')

        file_name = report.report_file.name
        if not default_storage.exists(file_name):
            repaired = self._repair_missing_file(report)
            if not repaired:
                raise Http404('Report file not available.')

        try:
            report.report_file.open('rb')
        except Exception as exc:
            raise Http404('Report file not available.') from exc
        return report.report_file

    def _file_response(self, report, as_attachment):
        file_obj = self._open_report_file(report)

        return FileResponse(
            file_obj,
            as_attachment=as_attachment,
            filename=self._build_download_filename(report),
        )

    def _download_response(self, report):
        return self._file_response(report, as_attachment=True)

    def _view_response(self, report):
        return self._file_response(report, as_attachment=False)


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
        report = self.scope_queryset_for_admin(MedicalReport.objects.filter(pk=pk)).first()
        if not report:
            raise Http404('Medical report not found.')
        return self._download_response(report)


class AdminMedicalReportViewFileView(AdminHospitalScopedQuerysetMixin, SuperAdminAndAdminOnlyMixin, MedicalReportDownloadMixin, View):
    """Allow admin/super-admin to open report files inline from detail pages."""

    def get(self, request, pk, *args, **kwargs):
        report = self.scope_queryset_for_admin(MedicalReport.objects.filter(pk=pk)).first()
        if not report:
            raise Http404('Medical report not found.')
        return self._view_response(report)
