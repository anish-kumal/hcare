from django.views import View
from django.views.generic import TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncMonth
from calendar import monthrange
from datetime import timedelta

from apps.appointments.models import Prescription
from apps.doctors.models import Doctor
from apps.hospitals.models import Hospital, HospitalDepartment, HospitalStaff
from apps.medical_report.models import MedicalReport
from apps.patients.models import Patient, PatientAppointment
from apps.payments.models import AppointmentPayment
from .forms import ContactMessageForm


# Create your views here.
class IndexView( TemplateView):
    """Render the home page"""
    template_name = 'patients/index.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            if user.is_super_admin:
                return redirect(reverse_lazy('super_admin_dashboard'))
            elif user.is_admin:
                return redirect(reverse_lazy('admin_dashboard'))
            elif user.is_doctor:
                return redirect(reverse_lazy('doctor_dashboard'))
            elif user.is_lab_assistant:
                return redirect(reverse_lazy('lab_assistant_dashboard'))
            elif user.is_pharmacist:
                return redirect(reverse_lazy('pharmacist_dashboard'))
            elif user.is_staff_member:
                return redirect(reverse_lazy('staff_dashboard'))

        return super().dispatch(request, *args, **kwargs)



class AdministrView(TemplateView):
    """Render the hospital onboarding landing page"""
    template_name = 'administer/index_administer.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            if user.is_super_admin:
                return redirect(reverse_lazy('super_admin_dashboard'))
            elif user.is_admin:
                return redirect(reverse_lazy('admin_dashboard'))
            elif user.is_doctor:
                return redirect(reverse_lazy('doctor_dashboard'))
            elif user.is_lab_assistant:
                return redirect(reverse_lazy('lab_assistant_dashboard'))
            elif user.is_pharmacist:
                return redirect(reverse_lazy('pharmacist_dashboard'))
            elif user.is_staff_member:
                return redirect(reverse_lazy('staff_dashboard'))
            elif user.is_patient:
                return redirect(reverse_lazy('patient_dashboard'))
        return super().dispatch(request, *args, **kwargs)


class AboutView(TemplateView):
    """Render the public About page"""
    template_name = 'base/about.html'


class TermsView(TemplateView):
    """Render the public Terms page"""
    template_name = 'base/terms.html'


class PrivacyPolicyView(TemplateView):
    """Render the public Privacy Policy page"""
    template_name = 'base/privacy_policy.html'


class ServicesView(TemplateView):
    """Render the public Services page"""
    template_name = 'base/services.html'


class ContactView(FormView):
    """Render and handle the public Contact page form"""
    template_name = 'base/contact.html'
    form_class = ContactMessageForm
    success_url = reverse_lazy('contact')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Your message has been sent successfully.")
        return super().form_valid(form)


class SuperAdminDashboardView(LoginRequiredMixin, TemplateView):
    """Super Admin Dashboard"""
    template_name = 'super_admin/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_super_admin:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """Admin Dashboard"""
    template_name = 'admin/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)

    def _get_period_range(self):
        period = self.request.GET.get('period', 'week').strip().lower()
        today = timezone.localdate()

        if period == 'month':
            start_date = today.replace(day=1)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])
            period_label = 'This Month'
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
            period_label = 'This Year'
        else:
            period = 'week'
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
            period_label = 'This Week'

        return period, period_label, start_date, end_date

    def _format_amount_k(self, amount):
        amount = float(amount or 0)
        if amount >= 1000000:
            return f"{amount / 1000000:.1f}M"
        if amount >= 1000:
            return f"{amount / 1000:.1f}K"
        return f"{amount:.0f}"

    def _build_chart_data(self, period, start_date, end_date, appointment_queryset, payment_queryset):
        if period == 'year':
            date_keys = [start_date.replace(month=month, day=1) for month in range(1, 13)]
            labels = [date_key.strftime('%b') for date_key in date_keys]

            appointment_map = {date_key: 0 for date_key in date_keys}
            payment_map = {date_key: 0.0 for date_key in date_keys}

            appointment_rows = (
                appointment_queryset.filter(created__date__range=(start_date, end_date))
                .annotate(bucket=TruncMonth('created'))
                .values('bucket')
                .annotate(total=Count('id'))
            )
            for row in appointment_rows:
                bucket = row['bucket'].date().replace(day=1)
                appointment_map[bucket] = row['total']

            payment_rows = (
                payment_queryset.filter(
                    status=AppointmentPayment.PaymentStatus.PAID,
                    created__date__range=(start_date, end_date),
                )
                .annotate(bucket=TruncMonth('created'))
                .values('bucket')
                .annotate(total=Sum('amount'))
            )
            for row in payment_rows:
                bucket = row['bucket'].date().replace(day=1)
                payment_map[bucket] = float(row['total'] or 0)

        else:
            if period == 'month':
                week_keys = [1, 2, 3, 4, 5]
                date_keys = week_keys
                labels = [f'Week {week_number}' for week_number in week_keys]

                appointment_map = {week_number: 0 for week_number in week_keys}
                payment_map = {week_number: 0.0 for week_number in week_keys}

                appointment_rows = (
                    appointment_queryset.filter(created__date__range=(start_date, end_date))
                    .annotate(bucket=TruncDate('created'))
                    .values('bucket')
                    .annotate(total=Count('id'))
                )
                for row in appointment_rows:
                    bucket_day = row['bucket'].day
                    week_number = min(((bucket_day - 1) // 7) + 1, 5)
                    appointment_map[week_number] += row['total']

                payment_rows = (
                    payment_queryset.filter(
                        status=AppointmentPayment.PaymentStatus.PAID,
                        created__date__range=(start_date, end_date),
                    )
                    .annotate(bucket=TruncDate('created'))
                    .values('bucket')
                    .annotate(total=Sum('amount'))
                )
                for row in payment_rows:
                    bucket_day = row['bucket'].day
                    week_number = min(((bucket_day - 1) // 7) + 1, 5)
                    payment_map[week_number] += float(row['total'] or 0)
            else:
                date_keys = [start_date + timedelta(days=offset) for offset in range(7)]
                labels = [date_key.strftime('%a %d') for date_key in date_keys]

                appointment_map = {date_key: 0 for date_key in date_keys}
                payment_map = {date_key: 0.0 for date_key in date_keys}

                appointment_rows = (
                    appointment_queryset.filter(created__date__range=(start_date, end_date))
                    .annotate(bucket=TruncDate('created'))
                    .values('bucket')
                    .annotate(total=Count('id'))
                )
                for row in appointment_rows:
                    appointment_map[row['bucket']] = row['total']

                payment_rows = (
                    payment_queryset.filter(
                        status=AppointmentPayment.PaymentStatus.PAID,
                        created__date__range=(start_date, end_date),
                    )
                    .annotate(bucket=TruncDate('created'))
                    .values('bucket')
                    .annotate(total=Sum('amount'))
                )
                for row in payment_rows:
                    payment_map[row['bucket']] = float(row['total'] or 0)

        return {
            'labels': labels,
            'appointments': [appointment_map[date_key] for date_key in date_keys],
            'income': [payment_map[date_key] for date_key in date_keys],
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital_id = getattr(self.request, 'admin_hospital_id', None)
        period, period_label, start_date, end_date = self._get_period_range()

        hospital_queryset = Hospital.objects.all()
        doctor_queryset = Doctor.objects.all()
        appointment_queryset = PatientAppointment.objects.all()
        payment_queryset = AppointmentPayment.objects.all()
        prescription_queryset = Prescription.objects.all()
        report_queryset = MedicalReport.objects.all()
        staff_queryset = HospitalStaff.objects.all()
        department_queryset = HospitalDepartment.objects.all()

        if hospital_id:
            hospital_queryset = hospital_queryset.filter(pk=hospital_id)
            doctor_queryset = doctor_queryset.filter(hospital_id=hospital_id)
            appointment_queryset = appointment_queryset.filter(hospital_id=hospital_id)
            payment_queryset = payment_queryset.filter(appointment__hospital_id=hospital_id)
            prescription_queryset = prescription_queryset.filter(appointment__hospital_id=hospital_id)
            report_queryset = report_queryset.filter(primary_hospital_id=hospital_id)
            staff_queryset = staff_queryset.filter(hospital_id=hospital_id)
            department_queryset = department_queryset.filter(hospital_id=hospital_id)

        hospital = hospital_queryset.first()
        context['hospital_name'] = hospital.name if hospital else 'Hospital'
        context['hospital_is_active'] = hospital.is_active if hospital else False
        context['selected_period'] = period
        context['selected_period_label'] = period_label
        context['period_choices'] = [
            ('week', 'This Week'),
            ('month', 'This Month'),
            ('year', 'This Year'),
        ]

        

        context['staff_count'] = staff_queryset.count()
        context['doctor_count'] = doctor_queryset.count()

        total_income = (
            payment_queryset.filter(status=AppointmentPayment.PaymentStatus.PAID)
            .aggregate(total=Sum('amount'))
            .get('total')
            or 0
        )
        period_income = (
            payment_queryset.filter(
                status=AppointmentPayment.PaymentStatus.PAID,
                created__date__range=(start_date, end_date),
            )
            .aggregate(total=Sum('amount'))
            .get('total')
            or 0
        )

        context['total_income_display'] = f"{self._format_amount_k(total_income)}"
        context['period_income_display'] = f"{self._format_amount_k(period_income)}"
        context['dashboard_chart_data'] = self._build_chart_data(
            period,
            start_date,
            end_date,
            appointment_queryset,
            payment_queryset,
        )


        context['period_analytics_cards'] = [
            {
                'label': 'Total Income (NRs) ',
                'value': context['period_income_display'],
                'icon': 'account_balance_wallet',
            },
            {
                'label': 'Appointments',
                'value': appointment_queryset.filter(created__date__range=(start_date, end_date)).count(),
                'icon': 'event_available',
            },
            {
                'label': 'Payments',
                'value': payment_queryset.filter(created__date__range=(start_date, end_date)).count(),
                'icon': 'paid',
            },
            {
                'label': 'Prescriptions',
                'value': prescription_queryset.filter(created__date__range=(start_date, end_date)).count(),
                'icon': 'description',
            },
            {
                'label': 'Medical Reports',
                'value': report_queryset.filter(created__date__range=(start_date, end_date)).count(),
                'icon': 'file_present',
            },
        ]

        return context


class DoctorDashboardView(LoginRequiredMixin, TemplateView):
    """Doctor Dashboard"""
    template_name = 'doctors/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_doctor:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class PatientDashboardView(LoginRequiredMixin, TemplateView):
    """Patient Dashboard"""
    template_name = 'patients/index.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_patient:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class LabAssistantDashboardView(LoginRequiredMixin, TemplateView):
    """Lab Assistant Dashboard"""
    template_name = 'lab_assistant/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_lab_assistant:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)

class StaffDashboardView(LoginRequiredMixin, TemplateView):
    """Staff Dashboard"""
    template_name = 'staff/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff_member:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class PharmacistDashboardView(LoginRequiredMixin, TemplateView):
    """Pharmacist Dashboard"""
    template_name = 'pharmacist/dashboard.html'
    login_url = 'users:login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_pharmacist:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class Custom404View(View):
    def dispatch(self, request, *args, **kwargs):
        return render(request, 'custom/404.html', status=404)


class Custom500View(View):
    def dispatch(self, request, *args, **kwargs):
        return render(request, 'custom/500.html', status=500)
