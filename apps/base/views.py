from django.views import View
from django.views.generic import TemplateView, FormView
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q, Sum
from auditlog.models import LogEntry
from calendar import monthrange
from datetime import date, datetime, timedelta

from django.db.models.functions import TruncDate, TruncMonth

from apps.appointments.models import Prescription
from apps.doctors.models import Doctor
from apps.hospitals.models import Hospital, HospitalAdmin, HospitalStaff
from apps.medical_report.models import MedicalReport
from apps.patients.models import Patient, PatientAppointment
from apps.payments.models import AppointmentPayment
from .forms import ContactMessageForm


def _audit_chart_scope_from_request(request):
    """GET audit_period: 7d, 14d, this_month, last_month, year (this year by month)."""
    p = (request.GET.get('audit_period') or '7d').strip().lower()
    allowed = {'7d', '14d', 'this_month', 'last_month', 'year'}
    if p not in allowed:
        p = '7d'
    today = timezone.localdate()
    labels = {
        '7d': 'Last 7 days',
        '14d': 'Last 14 days',
        'this_month': 'This month (daily)',
        'last_month': 'Last month (daily)',
        'year': 'This year (by month)',
    }
    if p == '7d':
        return p, labels[p], today - timedelta(days=6), today, 'day'
    if p == '14d':
        return p, labels[p], today - timedelta(days=13), today, 'day'
    if p == 'this_month':
        return p, labels[p], today.replace(day=1), today, 'day'
    if p == 'last_month':
        first_this = today.replace(day=1)
        end_prev = first_this - timedelta(days=1)
        start_prev = end_prev.replace(day=1)
        return p, labels[p], start_prev, end_prev, 'day'
    return 'year', labels['year'], today.replace(month=1, day=1), today, 'month'


def _normalize_trunc_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return timezone.localtime(value).date() if timezone.is_aware(value) else value.date()
    if isinstance(value, date):
        return value
    return value


def _build_audit_log_chart_series(log_queryset, start_date, end_date, granularity):
    """Labels + create/update/delete series for ApexCharts (aligned with auditlog action ints)."""
    if granularity == 'day':
        date_keys = []
        cur = start_date
        while cur <= end_date:
            date_keys.append(cur)
            cur += timedelta(days=1)
        n = len(date_keys)
        if n > 14:
            labels = [d.strftime('%d %b') for d in date_keys]
        elif n > 7:
            labels = [d.strftime('%a %d') for d in date_keys]
        else:
            labels = [d.strftime('%a %d') for d in date_keys]
        create_map = {k: 0 for k in date_keys}
        update_map = {k: 0 for k in date_keys}
        delete_map = {k: 0 for k in date_keys}
        rows = (
            log_queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            .annotate(bucket=TruncDate('timestamp'))
            .values('bucket', 'action')
            .annotate(c=Count('pk'))
        )
        for row in rows:
            bd = _normalize_trunc_date(row['bucket'])
            if bd is None or bd not in create_map:
                continue
            c = row['c']
            a = row['action']
            if a == 0:
                create_map[bd] += c
            elif a == 1:
                update_map[bd] += c
            elif a == 2:
                delete_map[bd] += c
        return {
            'labels': labels,
            'audit_create': [create_map[k] for k in date_keys],
            'audit_update': [update_map[k] for k in date_keys],
            'audit_delete': [delete_map[k] for k in date_keys],
        }

    date_keys = [start_date.replace(month=m, day=1) for m in range(1, 13)]
    labels = [k.strftime('%b') for k in date_keys]
    create_map = {k: 0 for k in date_keys}
    update_map = {k: 0 for k in date_keys}
    delete_map = {k: 0 for k in date_keys}
    rows = (
        log_queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
        .annotate(bucket=TruncMonth('timestamp'))
        .values('bucket', 'action')
        .annotate(c=Count('pk'))
    )
    for row in rows:
        raw = row['bucket']
        raw = _normalize_trunc_date(raw) if raw is not None else None
        if raw is None:
            continue
        bm = date(raw.year, raw.month, 1)
        if bm not in create_map:
            continue
        c = row['c']
        a = row['action']
        if a == 0:
            create_map[bm] += c
        elif a == 1:
            update_map[bm] += c
        elif a == 2:
            delete_map[bm] += c
    return {
        'labels': labels,
        'audit_create': [create_map[k] for k in date_keys],
        'audit_update': [update_map[k] for k in date_keys],
        'audit_delete': [delete_map[k] for k in date_keys],
    }


def _paid_reference_datetime(paid_at, created):
    return paid_at if paid_at is not None else created


def _build_operational_chart_data(
    period, start_date, end_date, appointment_queryset, payment_queryset
):
    """Visits (scheduled date), appointments created, paid income — same buckets as admin dashboard (no audit)."""

    def local_d(dt):
        if dt is None:
            return None
        if timezone.is_aware(dt):
            return timezone.localtime(dt).date()
        return dt.date() if hasattr(dt, 'date') else dt

    def bucket_key(d):
        if period == 'year':
            return date(d.year, d.month, 1)
        if period == 'month':
            return min(((d.day - 1) // 7) + 1, 5)
        return d

    if period == 'year':
        date_keys = [start_date.replace(month=m, day=1) for m in range(1, 13)]
        labels = [k.strftime('%b') for k in date_keys]
    elif period == 'month':
        date_keys = [1, 2, 3, 4, 5]
        labels = [f'Week {w}' for w in date_keys]
    else:
        week_day_count = max(1, (end_date - start_date).days + 1)
        date_keys = [start_date + timedelta(days=offset) for offset in range(week_day_count)]
        labels = [k.strftime('%a %d') for k in date_keys]

    visit_map = {k: 0 for k in date_keys}
    for ad in appointment_queryset.filter(
        appointment_date__gte=start_date,
        appointment_date__lte=end_date,
    ).values_list('appointment_date', flat=True):
        if ad is None:
            continue
        k = bucket_key(ad)
        if k in visit_map:
            visit_map[k] += 1

    created_map = {k: 0 for k in date_keys}
    for t in appointment_queryset.filter(
        created__date__gte=start_date,
        created__date__lte=end_date,
    ).values_list('created', flat=True):
        d = local_d(t)
        if d is None:
            continue
        k = bucket_key(d)
        if k in created_map:
            created_map[k] += 1

    income_map = {k: 0.0 for k in date_keys}
    for paid_at, created, amount in payment_queryset.filter(
        status=AppointmentPayment.PaymentStatus.PAID
    ).values_list('paid_at', 'created', 'amount'):
        ref = _paid_reference_datetime(paid_at, created)
        if ref is None:
            continue
        d = local_d(ref)
        if d is None or not (start_date <= d <= end_date):
            continue
        k = bucket_key(d)
        if k in income_map:
            income_map[k] += float(amount or 0)

    chart_payload = {
        'labels': labels,
        'appointments_visit': [visit_map[k] for k in date_keys],
        'appointments_created': [created_map[k] for k in date_keys],
        'income_paid': [income_map[k] for k in date_keys],
    }
    return chart_payload, date_keys


def appointment_trend_chart_payload(scope, start_date, end_date, appointment_qs):
    """Single-series appointment trend (doctor dashboard chart); works for any scoped queryset."""
    split_off = {
        'show_today_time_split': False,
        'today_index': None,
        'today_past_count': 0,
        'today_future_count': 0,
    }

    if scope == 'year':
        date_list = list(
            appointment_qs.filter(
                appointment_date__gte=start_date,
                appointment_date__lte=end_date,
            ).values_list('appointment_date', flat=True)
        )
        date_keys = [start_date.replace(month=m, day=1) for m in range(1, 13)]
        labels = [d.strftime('%b') for d in date_keys]
        appointment_map = {k: 0 for k in date_keys}
        for ad in date_list:
            if ad is None:
                continue
            k = date(ad.year, ad.month, 1)
            if k in appointment_map:
                appointment_map[k] += 1
        return {
            'labels': labels,
            'appointments': [appointment_map[k] for k in date_keys],
            **split_off,
        }

    if scope == 'month':
        date_list = list(
            appointment_qs.filter(
                appointment_date__gte=start_date,
                appointment_date__lte=end_date,
            ).values_list('appointment_date', flat=True)
        )
        week_keys = [1, 2, 3, 4, 5]
        date_keys = week_keys
        labels = [f'Week {w}' for w in week_keys]
        appointment_map = {w: 0 for w in week_keys}
        for ad in date_list:
            if ad is None:
                continue
            day = ad.day
            week_number = min(((day - 1) // 7) + 1, 5)
            appointment_map[week_number] += 1
        return {
            'labels': labels,
            'appointments': [appointment_map[k] for k in date_keys],
            **split_off,
        }

    date_keys = [start_date + timedelta(days=offset) for offset in range(7)]
    today_local = timezone.localdate()
    now = timezone.now()
    tz = timezone.get_current_timezone()
    today_idx = None
    labels = []
    for d in date_keys:
        if d == today_local:
            labels.append(f"{d.strftime('%a %d')} · Today")
            today_idx = len(labels) - 1
        else:
            labels.append(d.strftime('%a %d'))
    appointment_map = {k: 0 for k in date_keys}
    today_past_count = 0
    today_future_count = 0
    rows = appointment_qs.filter(
        appointment_date__gte=start_date,
        appointment_date__lte=end_date,
    ).values_list('appointment_date', 'appointment_time')
    for ad, at in rows:
        if ad is None or at is None:
            continue
        if ad in appointment_map:
            appointment_map[ad] += 1
        if ad == today_local:
            slot_naive = datetime.combine(ad, at)
            if settings.USE_TZ:
                slot = timezone.make_aware(slot_naive, tz)
            else:
                slot = slot_naive
            if slot <= now:
                today_past_count += 1
            else:
                today_future_count += 1
    return {
        'labels': labels,
        'appointments': [appointment_map[k] for k in date_keys],
        'show_today_time_split': True,
        'today_index': today_idx,
        'today_past_count': today_past_count,
        'today_future_count': today_future_count,
    }


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

class AdministerAboutView(TemplateView):
    """Render the public About page for hospital onboarding"""
    template_name = 'base/about_administer.html'

class HowItWorksView(TemplateView):
    """Render the public How It Works page for hospital onboarding"""
    template_name = 'base/How_it_works.html'

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


class AdministerContactView(FormView):
    """Render the public Contact page for hospital onboarding"""
    template_name = 'base/contact_administer.html'  
    form_class = ContactMessageForm
    success_url = reverse_lazy('contact')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Your message has been sent successfully.")
        return super().form_valid(form)

class AdministerPricingView(TemplateView):
    """Render the public Pricing page for hospital onboarding"""
    template_name = 'base/pricing.html'
    

class SuperAdminDashboardView(LoginRequiredMixin, TemplateView):
    """Platform overview: users, hospitals, patients, appointments by period, chart, top hospitals."""
    template_name = 'super_admin/dashboard.html'
    login_url = 'users:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_super_admin:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)

    def _format_compact_int(self, n):
        n = int(n or 0)
        if n >= 1_000_000:
            s = f'{n / 1_000_000:.1f}M'
        elif n >= 1000:
            s = f'{n / 1000:.1f}k'
        else:
            return str(n)
        return s.rstrip('0').rstrip('.')

    def _super_admin_chart_scope(self):
        scope = self.request.GET.get('chart_period', 'week').strip().lower()
        if scope not in {'week', 'month', 'year'}:
            scope = 'week'
        today = timezone.localdate()
        if scope == 'month':
            start_date = today.replace(day=1)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])
            label = 'This month'
        elif scope == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
            label = 'This year'
        else:
            scope = 'week'
            start_date = today - timedelta(days=6)
            end_date = today
            label = 'Last 7 days'
        return scope, label, start_date, end_date

    def _build_super_admin_appointment_chart(self, scope, start_date, end_date, appointment_qs):
        date_list = list(
            appointment_qs.filter(
                appointment_date__gte=start_date,
                appointment_date__lte=end_date,
            ).values_list('appointment_date', flat=True)
        )

        if scope == 'year':
            date_keys = [start_date.replace(month=m, day=1) for m in range(1, 13)]
            labels = [d.strftime('%b') for d in date_keys]
            appointment_map = {k: 0 for k in date_keys}
            for ad in date_list:
                if ad is None:
                    continue
                k = date(ad.year, ad.month, 1)
                if k in appointment_map:
                    appointment_map[k] += 1

        elif scope == 'month':
            week_keys = [1, 2, 3, 4, 5]
            date_keys = week_keys
            labels = [f'Week {w}' for w in week_keys]
            appointment_map = {w: 0 for w in week_keys}
            for ad in date_list:
                if ad is None:
                    continue
                day = ad.day
                week_number = min(((day - 1) // 7) + 1, 5)
                appointment_map[week_number] += 1

        else:
            week_day_count = max(1, (end_date - start_date).days + 1)
            date_keys = [start_date + timedelta(days=offset) for offset in range(week_day_count)]
            labels = [d.strftime('%a %d') for d in date_keys]
            appointment_map = {k: 0 for k in date_keys}
            for ad in date_list:
                if ad is None:
                    continue
                if ad in appointment_map:
                    appointment_map[ad] += 1

        return {
            'labels': labels,
            'appointments': [appointment_map[k] for k in date_keys],
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        today = timezone.localdate()

        non_super = User.objects.exclude(user_type=User.UserType.SUPER_ADMIN)
        context['total_users'] = non_super.filter(is_active=True).count()
        context['total_hospitals'] = Hospital.objects.count()
        context['total_patients'] = Patient.objects.count()

        week_start = today - timedelta(days=6)
        week_end = today
        month_start = today.replace(day=1)
        month_end = today.replace(day=monthrange(today.year, today.month)[1])
        year_start = today.replace(month=1, day=1)
        year_end = today.replace(month=12, day=31)

        appt_base = PatientAppointment.objects.all()
        context['appointments_last_7_days'] = appt_base.filter(
            appointment_date__range=(week_start, week_end)
        ).count()
        context['appointments_this_month'] = appt_base.filter(
            appointment_date__range=(month_start, month_end)
        ).count()
        context['appointments_this_year'] = appt_base.filter(
            appointment_date__range=(year_start, year_end)
        ).count()
        context['appointments_all_time'] = appt_base.count()

        scope, chart_label, c_start, c_end = self._super_admin_chart_scope()
        context['chart_period'] = scope
        context['chart_period_label'] = chart_label
        context['chart_period_choices'] = [
            ('week', 'Last 7 days'),
            ('month', 'This month'),
            ('year', 'This year'),
        ]
        context['super_admin_chart_data'] = self._build_super_admin_appointment_chart(
            scope,
            c_start,
            c_end,
            appt_base,
        )

        top_qs = (
            Hospital.objects.annotate(visit_count=Count('patient_appointments'))
            .order_by('-visit_count', 'name')[:4]
        )
        context['top_hospitals'] = [
            {
                'hospital': h,
                'visits_display': self._format_compact_int(h.visit_count),
            }
            for h in top_qs
        ]

        audit_key, audit_label, a_start, a_end, a_gran = _audit_chart_scope_from_request(
            self.request
        )
        context['audit_period'] = audit_key
        context['audit_period_label'] = audit_label
        context['audit_period_choices'] = [
            ('7d', 'Last 7 days'),
            ('14d', 'Last 14 days'),
            ('this_month', 'This month (daily)'),
            ('last_month', 'Last month (daily)'),
            ('year', 'This year (by month)'),
        ]
        context['super_admin_audit_chart_data'] = _build_audit_log_chart_series(
            LogEntry.objects.all(),
            a_start,
            a_end,
            a_gran,
        )

        return context


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
            start_date = today - timedelta(days=6)
            end_date = today
            period_label = 'Last 7 days'

        return period, period_label, start_date, end_date

    def _format_amount_k(self, amount):
        amount = float(amount or 0)
        if amount >= 1000000:
            return f"{amount / 1000000:.1f}M"
        if amount >= 1000:
            return f"{amount / 1000:.1f}K"
        return f"{amount:.0f}"

    def _paid_reference_datetime(self, paid_at, created):
        """Date used for “paid” charts: `paid_at` when set, else payment `created`."""
        return paid_at if paid_at is not None else created

    def _period_paid_stats(self, payment_queryset, start_date, end_date):
        """Total NPR and count of PAID rows whose paid reference day falls in [start_date, end_date]."""
        total = 0.0
        count = 0
        for paid_at, created, amount in payment_queryset.filter(
            status=AppointmentPayment.PaymentStatus.PAID
        ).values_list('paid_at', 'created', 'amount'):
            ref = self._paid_reference_datetime(paid_at, created)
            if ref is None:
                continue
            d = timezone.localtime(ref).date() if timezone.is_aware(ref) else ref.date()
            if start_date <= d <= end_date:
                total += float(amount or 0)
                count += 1
        return total, count

    def _get_hospital_user_ids_for_audit(self, hospital):
        """User IDs tied to this hospital (same scope as logs:auditlog_list for hospital admins)."""
        user_ids = set()
        user_ids.update(
            Doctor.objects.filter(hospital=hospital).values_list('user_id', flat=True)
        )
        user_ids.update(
            HospitalStaff.objects.filter(hospital=hospital).values_list('user_id', flat=True)
        )
        user_ids.update(
            HospitalAdmin.objects.filter(hospital=hospital).values_list('user_id', flat=True)
        )
        user_ids.update(Patient.objects.filter(hospital=hospital).values_list('user_id', flat=True))
        user_ids.update(
            Patient.objects.filter(appointments__hospital=hospital)
            .distinct()
            .values_list('user_id', flat=True)
        )
        return [uid for uid in user_ids if uid is not None]

    def _build_chart_data(
        self,
        period,
        start_date,
        end_date,
        appointment_queryset,
        payment_queryset,
        hospital=None,
    ):
        """Visit, created, income charts; audit chart matches hospital audit log (actor scope)."""

        def local_d(dt):
            if dt is None:
                return None
            if timezone.is_aware(dt):
                return timezone.localtime(dt).date()
            return dt.date() if hasattr(dt, 'date') else dt

        def bucket_key(d):
            if period == 'year':
                return date(d.year, d.month, 1)
            if period == 'month':
                return min(((d.day - 1) // 7) + 1, 5)
            return d

        op, date_keys = _build_operational_chart_data(
            period,
            start_date,
            end_date,
            appointment_queryset,
            payment_queryset,
        )

        create_map = {k: 0 for k in date_keys}
        update_map = {k: 0 for k in date_keys}
        delete_map = {k: 0 for k in date_keys}
        if hospital:
            actor_ids = self._get_hospital_user_ids_for_audit(hospital)
            if actor_ids:
                for ts, action in LogEntry.objects.filter(
                    actor_id__in=actor_ids,
                    timestamp__date__gte=start_date,
                    timestamp__date__lte=end_date,
                ).values_list('timestamp', 'action'):
                    d = local_d(ts)
                    if d is None or not (start_date <= d <= end_date):
                        continue
                    key = bucket_key(d)
                    if key not in create_map:
                        continue
                    if action == 0:
                        create_map[key] += 1
                    elif action == 1:
                        update_map[key] += 1
                    elif action == 2:
                        delete_map[key] += 1

        return {
            **op,
            'audit_create': [create_map[k] for k in date_keys],
            'audit_update': [update_map[k] for k in date_keys],
            'audit_delete': [delete_map[k] for k in date_keys],
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

        if hospital_id:
            hospital_queryset = hospital_queryset.filter(pk=hospital_id)
            doctor_queryset = doctor_queryset.filter(hospital_id=hospital_id)
            appointment_queryset = appointment_queryset.filter(hospital_id=hospital_id)
            payment_queryset = payment_queryset.filter(appointment__hospital_id=hospital_id)
            prescription_queryset = prescription_queryset.filter(appointment__hospital_id=hospital_id)
            report_queryset = report_queryset.filter(primary_hospital_id=hospital_id)
            staff_queryset = staff_queryset.filter(hospital_id=hospital_id)

        hospital = hospital_queryset.first()
        context['hospital_name'] = hospital.name if hospital else 'Hospital'
        context['hospital_is_active'] = hospital.is_active if hospital else False
        context['selected_period'] = period
        context['selected_period_label'] = period_label
        context['period_choices'] = [
            ('week', 'Last 7 days'),
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
        period_income, period_paid_count = self._period_paid_stats(
            payment_queryset, start_date, end_date
        )

        context['total_income_display'] = f"{self._format_amount_k(total_income)}"
        context['period_income_display'] = f"{self._format_amount_k(period_income)}"
        context['period_paid_count'] = period_paid_count
        context['dashboard_chart_data'] = self._build_chart_data(
            period,
            start_date,
            end_date,
            appointment_queryset,
            payment_queryset,
            hospital,
        )


        context['period_analytics_cards'] = [
            {
                'label': 'Income (paid date)',
                'value': context['period_income_display'],
                'icon': 'account_balance_wallet',
            },
            {
                'label': 'Visits (scheduled date)',
                'value': appointment_queryset.filter(
                    appointment_date__range=(start_date, end_date)
                ).count(),
                'icon': 'calendar_month',
            },
            {
                'label': 'Appointments created',
                'value': appointment_queryset.filter(
                    created__date__range=(start_date, end_date)
                ).count(),
                'icon': 'add_circle',
            },
            {
                'label': 'Paid payments',
                'value': context['period_paid_count'],
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
    """Simple doctor overview: counts by period (like super admin) + one appointment trend chart."""

    template_name = 'doctors/dashboard.html'
    login_url = 'users:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_doctor:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)

    def _doctor_chart_scope(self):
        scope = self.request.GET.get('chart_period', 'week').strip().lower()
        if scope not in {'week', 'month', 'year'}:
            scope = 'week'
        today = timezone.localdate()
        if scope == 'month':
            start_date = today.replace(day=1)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])
            label = 'This month'
        elif scope == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
            label = 'This year'
        else:
            scope = 'week'
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
            label = 'This week'
        return scope, label, start_date, end_date

    def _build_doctor_appointment_chart(self, scope, start_date, end_date, appointment_qs):
        return appointment_trend_chart_payload(scope, start_date, end_date, appointment_qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        try:
            doctor = Doctor.objects.select_related('hospital', 'user').get(user=user)
        except Doctor.DoesNotExist:
            context['doctor'] = None
            context['doctor_display_name'] = user.get_full_name() or user.username
            context['hospital_name'] = '—'
            context['appointments_this_week'] = 0
            context['appointments_this_month'] = 0
            context['appointments_this_year'] = 0
            context['appointments_all_time'] = 0
            context['upcoming_count'] = 0
            context['patient_count'] = 0
            context['next_visits'] = []
            scope, chart_label, c_start, c_end = self._doctor_chart_scope()
            context['chart_period'] = scope
            context['chart_period_label'] = chart_label
            context['chart_period_choices'] = [
                ('week', 'This week'),
                ('month', 'This month'),
                ('year', 'This year'),
            ]
            context['doctor_chart_data'] = {
                'labels': [],
                'appointments': [],
                'show_today_time_split': False,
                'today_index': None,
                'today_past_count': 0,
                'today_future_count': 0,
            }
            return context

        appt_base = PatientAppointment.objects.filter(doctor=doctor)

        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        month_start = today.replace(day=1)
        month_end = today.replace(day=monthrange(today.year, today.month)[1])
        year_start = today.replace(month=1, day=1)
        year_end = today.replace(month=12, day=31)

        context['doctor'] = doctor
        context['doctor_display_name'] = doctor.user.get_full_name() or doctor.user.username
        context['hospital_name'] = doctor.hospital.name if doctor.hospital_id else '—'
        context['appointments_this_week'] = appt_base.filter(
            appointment_date__range=(week_start, week_end)
        ).count()
        context['appointments_this_month'] = appt_base.filter(
            appointment_date__range=(month_start, month_end)
        ).count()
        context['appointments_this_year'] = appt_base.filter(
            appointment_date__range=(year_start, year_end)
        ).count()
        context['appointments_all_time'] = appt_base.count()

        upcoming_statuses = ('SCHEDULED', 'FOLLOW_UP', 'RESCHEDULED')
        context['upcoming_count'] = appt_base.filter(
            appointment_date__gte=today,
            status__in=upcoming_statuses,
        ).count()
        context['patient_count'] = (
            Patient.objects.filter(appointments__doctor=doctor).distinct().count()
        )

        context['next_visits'] = list(
            appt_base.filter(appointment_date__gte=today, status__in=upcoming_statuses)
            .select_related('patient__user', 'hospital')
            .order_by('appointment_date', 'appointment_time')[:4]
        )

        scope, chart_label, c_start, c_end = self._doctor_chart_scope()
        context['chart_period'] = scope
        context['chart_period_label'] = chart_label
        context['chart_period_choices'] = [
            ('week', 'This week'),
            ('month', 'This month'),
            ('year', 'This year'),
        ]
        context['doctor_chart_data'] = self._build_doctor_appointment_chart(
            scope,
            c_start,
            c_end,
            appt_base,
        )

        return context


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

    def _lab_report_chart_scope(self):
        scope = self.request.GET.get('chart_period', 'week').strip().lower()
        if scope not in {'week', 'month', 'year'}:
            scope = 'week'
        today = timezone.localdate()
        if scope == 'month':
            start_date = today.replace(day=1)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])
            label = 'This month'
        elif scope == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
            label = 'This year'
        else:
            scope = 'week'
            # Show last 7 days: today and previous 6 days
            start_date = today - timedelta(days=6)
            end_date = today
            label = 'Last 7 days'
        return scope, label, start_date, end_date

    def _build_lab_report_chart(self, scope, start_date, end_date, report_qs):
        # Similar to appointment_trend_chart_payload, but for MedicalReport.created
        if scope == 'year':
            date_keys = [start_date.replace(month=m, day=1) for m in range(1, 13)]
            labels = [d.strftime('%b') for d in date_keys]
            report_map = {k: 0 for k in date_keys}
            for created in report_qs.filter(created__date__gte=start_date, created__date__lte=end_date).values_list('created', flat=True):
                if created is None:
                    continue
                d = created.date() if hasattr(created, 'date') else created
                k = d.replace(day=1)
                if k in report_map:
                    report_map[k] += 1
            return {
                'labels': labels,
                'reports': [report_map[k] for k in date_keys],
            }
        if scope == 'month':
            week_keys = [1, 2, 3, 4, 5]
            labels = [f'Week {w}' for w in week_keys]
            report_map = {w: 0 for w in week_keys}
            for created in report_qs.filter(created__date__gte=start_date, created__date__lte=end_date).values_list('created', flat=True):
                if created is None:
                    continue
                d = created.date() if hasattr(created, 'date') else created
                day = d.day
                week_number = min(((day - 1) // 7) + 1, 5)
                report_map[week_number] += 1
            return {
                'labels': labels,
                'reports': [report_map[w] for w in week_keys],
            }
        # week
        date_keys = [start_date + timedelta(days=offset) for offset in range(7)]
        labels = [d.strftime('%a %d') for d in date_keys]
        report_map = {k: 0 for k in date_keys}
        for created in report_qs.filter(created__date__gte=start_date, created__date__lte=end_date).values_list('created', flat=True):
            if created is None:
                continue
            d = created.date() if hasattr(created, 'date') else created
            if d in report_map:
                report_map[d] += 1
        return {
            'labels': labels,
            'reports': [report_map[k] for k in date_keys],
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Chart data for medical reports
        scope, chart_label, start_date, end_date = self._lab_report_chart_scope()
        report_qs = MedicalReport.objects.all()
        context['chart_period'] = scope
        context['chart_period_label'] = chart_label
        context['chart_period_choices'] = [
            ('week', 'Last 7 days'),
            ('month', 'This month'),
            ('year', 'This year'),
        ]
        context['lab_report_chart_data'] = self._build_lab_report_chart(scope, start_date, end_date, report_qs)

        # Latest 4 medical reports
        context['latest_reports'] = list(report_qs.order_by('-created')[:4])

        # Report counts
        context['total_reports'] = report_qs.count()
        context['shared_reports'] = report_qs.filter(is_shared=True).count() if hasattr(MedicalReport, 'is_shared') else 0
        context['private_reports'] = report_qs.filter(is_shared=False).count() if hasattr(MedicalReport, 'is_shared') else 0

        return context

class StaffDashboardView(LoginRequiredMixin, TemplateView):
    """Front-desk dashboard: same appointment trend chart as doctors, scoped to the whole hospital."""

    template_name = 'staff/dashboard.html'
    login_url = 'users:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff_member:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)

    def _staff_chart_scope(self):
        """Match doctor dashboard: this week (Mon–Sun), this month, this year."""
        scope = self.request.GET.get('chart_period', 'week').strip().lower()
        if scope not in {'week', 'month', 'year'}:
            scope = 'week'
        today = timezone.localdate()
        if scope == 'month':
            start_date = today.replace(day=1)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])
            label = 'This month'
        elif scope == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
            label = 'This year'
        else:
            scope = 'week'
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
            label = 'This week'
        return scope, label, start_date, end_date

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        hospital_id = getattr(self.request, 'admin_hospital_id', None) or getattr(
            self.request, 'hospital_scope_id', None
        )
        if not hospital_id:
            try:
                hospital_id = self.request.user.hospital_staff_profile.hospital_id
            except HospitalStaff.DoesNotExist:
                hospital_id = None

        empty_chart = {
            'labels': [],
            'appointments': [],
            'show_today_time_split': False,
            'today_index': None,
            'today_past_count': 0,
            'today_future_count': 0,
        }
        empty = {
            'hospital_name': 'Hospital',
            'hospital_is_active': False,
            'patient_count': 0,
            'doctor_count': 0,
            'pending_payments_count': 0,
            'appointments_this_week': 0,
            'appointments_this_month': 0,
            'appointments_this_year': 0,
            'appointments_all_time': 0,
            'upcoming_count': 0,
            'next_visits': [],
            'chart_period': 'week',
            'chart_period_label': 'This week',
            'chart_period_choices': [
                ('week', 'This week'),
                ('month', 'This month'),
                ('year', 'This year'),
            ],
            'staff_chart_data': empty_chart,
        }
        if not hospital_id:
            context.update(empty)
            return context

        hospital = Hospital.objects.filter(pk=hospital_id).first()
        context['hospital_name'] = hospital.name if hospital else 'Hospital'
        context['hospital_is_active'] = bool(hospital and hospital.is_active)

        patient_base = Patient.objects.filter(
            Q(hospital_id=hospital_id) | Q(appointments__hospital_id=hospital_id)
        ).distinct()
        context['patient_count'] = patient_base.count()
        context['doctor_count'] = Doctor.objects.filter(hospital_id=hospital_id).count()


        appt_qs = PatientAppointment.objects.filter(hospital_id=hospital_id)

        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        month_start = today.replace(day=1)
        month_end = today.replace(day=monthrange(today.year, today.month)[1])
        year_start = today.replace(month=1, day=1)
        year_end = today.replace(month=12, day=31)

        context['appointments_this_week'] = appt_qs.filter(
            appointment_date__range=(week_start, week_end)
        ).count()
        context['appointments_this_month'] = appt_qs.filter(
            appointment_date__range=(month_start, month_end)
        ).count()
        context['appointments_this_year'] = appt_qs.filter(
            appointment_date__range=(year_start, year_end)
        ).count()
        context['appointments_all_time'] = appt_qs.count()

        upcoming_statuses = ('SCHEDULED', 'FOLLOW_UP', 'RESCHEDULED')
        context['upcoming_count'] = appt_qs.filter(
            appointment_date__gte=today,
            status__in=upcoming_statuses,
        ).count()

        payment_qs = AppointmentPayment.objects.filter(appointment__hospital_id=hospital_id)
        context['pending_payments_count'] = payment_qs.filter(
            status=AppointmentPayment.PaymentStatus.PENDING
        ).count()

        context['next_visits'] = list(
            appt_qs.filter(appointment_date__gte=today, status__in=upcoming_statuses)
            .select_related('patient__user', 'hospital', 'doctor__user')
            .order_by('appointment_date', 'appointment_time')[:4]
        )

        scope, chart_label, c_start, c_end = self._staff_chart_scope()
        context['chart_period'] = scope
        context['chart_period_label'] = chart_label
        context['chart_period_choices'] = [
            ('week', 'This week'),
            ('month', 'This month'),
            ('year', 'This year'),
        ]
        context['staff_chart_data'] = appointment_trend_chart_payload(
            scope,
            c_start,
            c_end,
            appt_qs,
        )

        return context


class PharmacistDashboardView(LoginRequiredMixin, TemplateView):
    """Pharmacist Dashboard: analytics and chart for prescriptions."""
    template_name = 'pharmacist/dashboard.html'
    login_url = 'users:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_pharmacist:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)

    def _pharmacist_chart_scope(self):
        scope = self.request.GET.get('chart_period', 'week').strip().lower()
        if scope not in {'week', 'month', 'year'}:
            scope = 'week'
        today = timezone.localdate()
        if scope == 'month':
            start_date = today.replace(day=1)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])
            label = 'This month'
        elif scope == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
            label = 'This year'
        else:
            scope = 'week'
            start_date = today - timedelta(days=6)
            end_date = today
            label = 'Last 7 days'
        return scope, label, start_date, end_date

    def _build_pharmacist_chart(self, scope, start_date, end_date, prescription_qs):
        # Chart: count of prescriptions by created date
        if scope == 'year':
            date_keys = [start_date.replace(month=m, day=1) for m in range(1, 13)]
            labels = [d.strftime('%b') for d in date_keys]
            pres_map = {k: 0 for k in date_keys}
            for created in prescription_qs.filter(created__date__gte=start_date, created__date__lte=end_date).values_list('created', flat=True):
                if created is None:
                    continue
                d = created.date() if hasattr(created, 'date') else created
                k = d.replace(day=1)
                if k in pres_map:
                    pres_map[k] += 1
            return {
                'labels': labels,
                'prescriptions': [pres_map[k] for k in date_keys],
            }
        if scope == 'month':
            week_keys = [1, 2, 3, 4, 5]
            labels = [f'Week {w}' for w in week_keys]
            pres_map = {w: 0 for w in week_keys}
            for created in prescription_qs.filter(created__date__gte=start_date, created__date__lte=end_date).values_list('created', flat=True):
                if created is None:
                    continue
                d = created.date() if hasattr(created, 'date') else created
                day = d.day
                week_number = min(((day - 1) // 7) + 1, 5)
                pres_map[week_number] += 1
            return {
                'labels': labels,
                'prescriptions': [pres_map[w] for w in week_keys],
            }
        # week
        date_keys = [start_date + timedelta(days=offset) for offset in range(7)]
        labels = [d.strftime('%a %d') for d in date_keys]
        pres_map = {k: 0 for k in date_keys}
        for created in prescription_qs.filter(created__date__gte=start_date, created__date__lte=end_date).values_list('created', flat=True):
            if created is None:
                continue
            d = created.date() if hasattr(created, 'date') else created
            if d in pres_map:
                pres_map[d] += 1
        return {
            'labels': labels,
            'prescriptions': [pres_map[k] for k in date_keys],
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Chart data for prescriptions
        scope, chart_label, start_date, end_date = self._pharmacist_chart_scope()
        prescription_qs = Prescription.objects.all()
        context['chart_period'] = scope
        context['chart_period_label'] = chart_label
        context['chart_period_choices'] = [
            ('week', 'Last 7 days'),
            ('month', 'This month'),
            ('year', 'This year'),
        ]
        context['pharmacist_chart_data'] = self._build_pharmacist_chart(scope, start_date, end_date, prescription_qs)

        # Latest 4 prescriptions
        context['latest_prescriptions'] = list(prescription_qs.order_by('-created')[:4])

        # Prescription counts
        context['total_prescriptions'] = prescription_qs.count()
        # New: prescriptions created today
        today = timezone.localdate()
        context['prescriptions_today'] = prescription_qs.filter(created__date=today).count()
        # New: prescriptions created this week (Monday to Sunday)
        last_7_days_start = today - timedelta(days=6)
        last_7_days_end = today
        context['prescriptions_last_7_days'] = prescription_qs.filter(created__date__range=(last_7_days_start, last_7_days_end)).count()
        context['prescriptions_this_month'] = prescription_qs.filter(created__date__month=today.month, created__date__year=today.year).count()
        context['prescriptions_this_year'] = prescription_qs.filter(created__date__year=today.year).count()

        return context

class Custom404View(View):
    def dispatch(self, request, *args, **kwargs):
        return render(request, 'custom/404.html', status=404)


class Custom500View(View):
    def dispatch(self, request, *args, **kwargs):
        return render(request, 'custom/500.html', status=500)

class Custom403View(View):
    def dispatch(self, request, *args, **kwargs):
        return render(request, 'custom/403.html', status=403)

class Custom400View(View):
    def dispatch(self, request, *args, **kwargs):
        return render(request, 'custom/400.html', status=400)

    