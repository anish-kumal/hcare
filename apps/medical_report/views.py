from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from apps.medical_report.models import MedicalReport
from apps.medical_report.forms import  AdminMedicalReportForm
from apps.base.mixin import SuperAdminAndAdminOnlyMixin
from django.urls import reverse_lazy

class AdminMedicalReportCreateView(SuperAdminAndAdminOnlyMixin, CreateView):
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

# Admin Views
class AdminMedicalReportListView(SuperAdminAndAdminOnlyMixin, ListView):
    """
    Admin view to list all medical reports
    """
    model = MedicalReport
    template_name = 'admin/medical_report_list.html'
    context_object_name = 'medical_reports'
    paginate_by = 20

    def get_queryset(self):
        return MedicalReport.objects.select_related('patient', 'primary_hospital', 'uploaded_by').all()


class AdminMedicalReportDetailView(SuperAdminAndAdminOnlyMixin, DetailView):
    """
    Admin view to show medical report details
    """
    model = MedicalReport
    template_name = 'admin/medical_report_detail.html'
    context_object_name = 'medical_report'

    def get_queryset(self):
        return MedicalReport.objects.select_related('patient', 'primary_hospital', 'uploaded_by').all()


class AdminMedicalReportUpdateView(SuperAdminAndAdminOnlyMixin, UpdateView):
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
        return MedicalReport.objects.select_related('patient', 'primary_hospital', 'uploaded_by').all()


class AdminMedicalReportDeleteView(SuperAdminAndAdminOnlyMixin, DeleteView):
    """
    Admin view to delete medical report
    """
    model = MedicalReport
    template_name = 'admin/medical_report_confirm_delete.html'
    success_url = reverse_lazy('medical_report:admin_medical_report_list')
