from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from datetime import datetime, timedelta
from apps.base.mixin import SuperAdminAndAdminOnlyMixin
from apps.doctors.models import Doctor
from apps.patients.models import Patient, PatientAppointment
from apps.payments.models import AppointmentPayment
from .forms import AppointmentBookingForm, AppointmentEditForm, AdminAppointmentBookingForm


ACTIVE_BOOKING_STATUSES = ['SCHEDULED', 'FOLLOW_UP', 'RESCHEDULED']





class PatientAccessMixin(LoginRequiredMixin):
    """Restrict appointment booking views to patient users."""
    login_url = 'users:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in first to continue.')
            return self.handle_no_permission()

        if not request.user.is_patient:
            messages.error(request, 'Only patients can access this page.')
            return redirect('index')

        return super().dispatch(request, *args, **kwargs)


def get_booking_status(patient, doctor, appointment_date, appointment_time, default_status):
    """Set follow-up when latest previous COMPLETED booking for same doctor is within 7 days."""
    previous_completed_appointment = PatientAppointment.objects.filter(
        patient_id=patient.id,
        doctor_id=doctor.id,
        status='COMPLETED',
        is_follow_up=False,
    ).filter(
        Q(appointment_date__lt=appointment_date)
        | Q(appointment_date=appointment_date, appointment_time__lt=appointment_time)
    ).order_by('-appointment_date', '-appointment_time').first()

    if not previous_completed_appointment:
        return default_status

    current_dt = timezone.make_aware(datetime.combine(appointment_date, appointment_time))
    previous_dt = timezone.make_aware(
        datetime.combine(
            previous_completed_appointment.appointment_date,
            previous_completed_appointment.appointment_time,
        )
    )

    if timedelta(0) <= (current_dt - previous_dt) <= timedelta(days=7):
        return 'FOLLOW_UP'

    return default_status


def has_existing_active_booking(patient, doctor):
    """Return True when patient already has an active booking within past 24 hours or upcoming with this doctor."""
    now = timezone.localtime()
    past_24_hours = now - timedelta(hours=24)
    
    return PatientAppointment.objects.filter(
        patient_id=patient.id,
        doctor_id=doctor.id,
        status__in=ACTIVE_BOOKING_STATUSES,
    ).filter(
        Q(appointment_date__gt=past_24_hours.date())  # Dates after past 24hrs
        | Q(appointment_date=past_24_hours.date(), appointment_time__gte=past_24_hours.time())  # Today at or after past 24hrs time
    ).exclude(
        appointment_date__lt=now.date(),  # Exclude past dates
        appointment_time__lt=now.time()  # And past times
    ).exists()





class DoctorDetailView( DetailView):
    """Show doctor details and available appointment slots"""
    model = Doctor
    template_name = 'appointments/doctor_detail.html'
    context_object_name = 'doctor'
    
    def get_queryset(self):
        return Doctor.objects.filter(
            is_available=True,
            is_active=True
        ).select_related('user', 'hospital').prefetch_related('schedules')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.object

        context['available_slots'] = doctor.get_available_slots_by_date(
            days=7,
            now=timezone.now(),
            active_statuses=ACTIVE_BOOKING_STATUSES,
        )
        context['doctor_full_name'] = f"Dr. {doctor.user.get_full_name()}"
        return context


class AppointmentCreateView(LoginRequiredMixin, CreateView):
    """Create an appointment booking"""
    model = PatientAppointment
    form_class = AppointmentBookingForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('appointments:booking_confirmation')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user is authenticated and has patient profile"""
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in first to continue.')
            return redirect('users:login')
        
        try:
            Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            messages.error(request, 'Please complete your patient profile before booking an appointment.')
            return redirect('patients:patient_profile_create')
        return super().dispatch(request, *args, **kwargs)
    
    def get_doctor(self):
        """Get the doctor from URL parameter"""
        doctor_id = self.kwargs.get('doctor_id')
        return get_object_or_404(Doctor, id=doctor_id, is_available=True, is_active=True)
    
    def get_patient(self):
        """Get the patient profile for the current user"""
        return Patient.objects.get(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            doctor = self.get_doctor()
            context['doctor'] = doctor
            context['doctor_full_name'] = f"Dr. {doctor.user.get_full_name()}"
            
            # Get appointment date and time from request
            appointment_date = self.request.GET.get('date')
            appointment_time = self.request.GET.get('time')
            context['appointment_date'] = appointment_date
            context['appointment_time'] = appointment_time
        except Doctor.DoesNotExist:
            messages.error(self.request, 'Doctor not found or is not available.')
            return redirect('appointments:doctor_list')
        
        return context
    
    def form_valid(self, form):
        """Process the form and create appointment"""
        try:
            doctor = self.get_doctor()
            patient = self.get_patient()
        except (Doctor.DoesNotExist, Patient.DoesNotExist):
            messages.error(self.request, 'Doctor or patient profile not found.')
            return redirect('appointments:doctor_list')
        
        appointment_date_str = self.request.POST.get('appointment_date')
        appointment_time_str = self.request.POST.get('appointment_time')
        
        # Validate dates
        try:
            appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
            appointment_time = datetime.strptime(appointment_time_str, '%H:%M').time()
        except (ValueError, TypeError):
            messages.error(self.request, 'Invalid date or time format.')
            return self.form_invalid(form)
        
        # Check if appointment is in the past
        appointment_datetime = datetime.combine(appointment_date, appointment_time)
        # Make datetime timezone-aware
        appointment_datetime = timezone.make_aware(appointment_datetime)
        if appointment_datetime < timezone.now():
            messages.error(self.request, 'Appointment date/time must be in the future.')
            return self.form_invalid(form)

        if has_existing_active_booking(patient=patient, doctor=doctor):
            messages.error(
                self.request,
                'You already have an active booking with this doctor. Please complete or cancel it before booking again.',
            )
            return self.form_invalid(form)
        
        # Validate selected slot against model-calculated availability for that date.
        weekday = appointment_date.weekday()
        schedules = doctor.schedules.filter(
            weekday=weekday,
            is_available=True,
        ).order_by('start_time')

        if not schedules:
            messages.error(self.request, 'Doctor is not available on that day.')
            return self.form_invalid(form)

        now = timezone.now()
        is_slot_available = False
        for schedule in schedules:
            available_slot_times = {
                slot['time']
                for slot in schedule.get_available_slots(
                    appointment_date=appointment_date,
                    now=now,
                    active_statuses=ACTIVE_BOOKING_STATUSES,
                )
            }
            if appointment_time in available_slot_times:
                is_slot_available = True
                break

        if not is_slot_available:
            messages.error(self.request, 'Selected slot is not available. Please choose another available time slot.')
            return self.form_invalid(form)
        
        # Create appointment
        appointment = form.save(commit=False)
        appointment.patient = patient
        appointment.doctor = doctor
        appointment.hospital = doctor.hospital
        appointment.appointment_date = appointment_date
        appointment.appointment_time = appointment_time
        appointment.status = get_booking_status(
            patient=patient,
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            default_status='SCHEDULED',
        )
        appointment.is_follow_up = appointment.status == 'FOLLOW_UP'
        appointment.save()

        # Set fee: 10 Rs for follow-up, consultation fee otherwise
        appointment_fee = 10 if appointment.status == 'FOLLOW_UP' else doctor.consultation_fee

        AppointmentPayment.objects.get_or_create(
            appointment=appointment,
            defaults={
                'amount': appointment_fee,
                'status': AppointmentPayment.PaymentStatus.PENDING,
                'payment_method': AppointmentPayment.PaymentMethod.CASH,
            },
        )
        
        messages.success(self.request, 'Appointment booked successfully! Please choose your payment method.')
        return redirect('payments:patient_payment_list')
    
    def form_invalid(self, form):
        """Handle invalid form"""
        return self.render_to_response(self.get_context_data(form=form))


class BookingConfirmationView(PatientAccessMixin, ListView):
    """Show recent bookings and confirmation"""
    template_name = 'appointments/booking_confirmation.html'
    context_object_name = 'appointments'
    
    def dispatch(self, request, *args, **kwargs):
        """Check if patient profile exists"""
        try:
            Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            messages.error(request, 'Please complete your patient profile before viewing appointments.')
            return redirect('patients:patient_profile_create')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        patient = Patient.objects.get(user=self.request.user)
        return PatientAppointment.objects.filter(
            patient=patient
        ).select_related('doctor', 'doctor__user', 'patient__user').order_by('-created')[:5]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = Patient.objects.get(user=self.request.user)
        
        # Get upcoming appointments
        context['upcoming_appointments'] = PatientAppointment.objects.filter(
            patient=patient,
            appointment_date__gte=timezone.now().date(),
            status__in=ACTIVE_BOOKING_STATUSES
        ).select_related('doctor', 'doctor__user').order_by('appointment_date', 'appointment_time')
        
        # Get past appointments
        context['past_appointments'] = PatientAppointment.objects.filter(
            patient=patient,
            appointment_date__lt=timezone.now().date()
        ).select_related('doctor', 'doctor__user').order_by('-appointment_date', '-appointment_time')
        
        return context


class AppointmentDetailView(PatientAccessMixin, DetailView):
    """View appointment details and edit appointment"""
    model = PatientAppointment
    template_name = 'appointments/appointment_detail.html'
    context_object_name = 'appointment'
    
    def get_queryset(self):
        """Only show appointments for the current patient"""
        patient = Patient.objects.filter(user=self.request.user).first()
        if not patient:
            return PatientAppointment.objects.none()
        return PatientAppointment.objects.filter(
            patient=patient
        ).select_related('doctor', 'doctor__user', 'doctor__hospital', 'payment')
    
    def post(self, request, *args, **kwargs):
        """Handle appointment update"""
        appointment = self.get_object()
        
        # Check if patient can still edit (only if not completed or cancelled)
        if appointment.status in ['COMPLETED', 'CANCELLED']:
            messages.error(request, 'Cannot edit completed or cancelled appointments.')
            return redirect('appointments:appointment_detail', pk=appointment.pk)
        
        form = AppointmentEditForm(request.POST, instance=appointment)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated successfully!')
            return redirect('appointments:appointment_detail', pk=appointment.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
            return self.get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment = self.object
        payment = getattr(appointment, 'payment', None)

        # Safely handle case where doctor might be None
        if appointment.doctor and appointment.doctor.user:
            context['doctor_full_name'] = f"Dr. {appointment.doctor.user.get_full_name()}"
        else:
            context['doctor_full_name'] = "Doctor"
        
        context['payment'] = payment
        context['show_khalti_pay_button'] = bool(
            payment and payment.status != AppointmentPayment.PaymentStatus.PAID
        )
        return context


class AppointmentDoctorListView(SuperAdminAndAdminOnlyMixin, ListView):
    """List all doctors for admin/staff to manage appointments""" 
    model = Doctor
    template_name = 'appointments/appointment_doctor_list.html'
    context_object_name = 'doctors'
    
    def get_queryset(self):
        queryset = Doctor.objects.filter(
            is_available=True,
            is_active=True
        ).select_related('user', 'hospital', 'department')

        selected_specialization = self.request.GET.get('specialization')
        if selected_specialization:
            queryset = queryset.filter(specialization=selected_specialization)

        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query)
                | Q(user__last_name__icontains=search_query)
                | Q(user__username__icontains=search_query)
                | Q(specialization__icontains=search_query)
                | Q(department__name__icontains=search_query)
                | Q(hospital__name__icontains=search_query)
            )

        return queryset.order_by('user__first_name', 'user__last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '').strip()
        context['selected_specialization'] = self.request.GET.get('specialization', '')
        context['specializations'] = Doctor.objects.filter(
            is_available=True,
            is_active=True,
            specialization__isnull=False,
        ).exclude(specialization='').values_list('specialization', flat=True).distinct().order_by('specialization')
        return context
    
class AppointmentDoctorScheduleView(SuperAdminAndAdminOnlyMixin, DetailView):
    """View doctor schedule and appointments for admin/staff"""
    model = Doctor
    template_name = 'appointments/appointment_doctor_schedule.html'
    context_object_name = 'doctor'
    booking_statuses = ACTIVE_BOOKING_STATUSES
    days_to_show = 7
    allowed_day_filters = (7, 14)
    
    def get_queryset(self):
        return Doctor.objects.filter(
            is_available=True,
            is_active=True
        ).select_related('user', 'hospital').prefetch_related('schedules', 'patient_appointments')

    def get_days_to_show(self):
        days_param = self.request.GET.get('days', '').strip()
        try:
            requested_days = int(days_param)
        except (TypeError, ValueError):
            return self.days_to_show
        if requested_days in self.allowed_day_filters:
            return requested_days
        return self.days_to_show

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.object
        selected_days = self.get_days_to_show()

        today = timezone.now().date()
        end_date = today + timedelta(days=selected_days - 1)
        now = timezone.now()

        schedules = doctor.schedules.filter(is_available=True).order_by('weekday', 'start_time')
        schedules_by_weekday = {}
        for schedule in schedules:
            schedules_by_weekday.setdefault(schedule.weekday, []).append(schedule)

        appointments = PatientAppointment.objects.filter(
            doctor=doctor,
            appointment_date__range=(today, end_date),
            status__in=self.booking_statuses,
        ).select_related('patient', 'patient__user').order_by('appointment_date', 'appointment_time')

        appointments_by_date = {}
        for appointment in appointments:
            appointments_by_date.setdefault(appointment.appointment_date, []).append(appointment)

        weekly_schedule = []
        for offset in range(selected_days):
            current_date = today + timedelta(days=offset)
            weekday = current_date.weekday()
            day_schedules = schedules_by_weekday.get(weekday, [])
            day_bookings = appointments_by_date.get(current_date, [])

            session_rows = []
            for schedule in day_schedules:
                session_bookings = [
                    booking
                    for booking in day_bookings
                    if schedule.start_time <= booking.appointment_time <= schedule.end_time
                ]
                booked_count = len(session_bookings)
                slots_left = max(schedule.max_patients - booked_count, 0)
                
                # Check if session end time has passed
                session_end_dt = timezone.make_aware(datetime.combine(current_date, schedule.end_time))
                is_past = session_end_dt <= now
                
                # Skip sessions that have already passed
                if is_past:
                    continue
                
                # Check if session is fully booked
                is_fully_booked = booked_count >= schedule.max_patients

                session_rows.append({
                    'schedule': schedule,
                    'booked_count': booked_count,
                    'slots_left': slots_left,
                    'bookings': session_bookings,
                    'is_fully_booked': is_fully_booked,
                    'is_bookable': not is_fully_booked,
                })

            daily_max_patients = sum(session['schedule'].max_patients for session in session_rows)
            daily_booked_count = sum(session['booked_count'] for session in session_rows)
            daily_slots_left = max(daily_max_patients - daily_booked_count, 0)
            
            # Day is bookable if at least one session is bookable
            day_is_bookable = any(session['is_bookable'] for session in session_rows)

            weekly_schedule.append({
                'date': current_date,
                'weekday': current_date.strftime('%A'),
                'sessions': session_rows,
                'has_schedule': bool(day_schedules),
                'daily_max_patients': daily_max_patients,
                'daily_booked_count': daily_booked_count,
                'daily_slots_left': daily_slots_left,
                'day_is_bookable': day_is_bookable,
                'all_bookings': day_bookings,
            })

        context['weekly_schedule'] = weekly_schedule
        context['doctor_full_name'] = f"Dr. {doctor.user.get_full_name()}"
        context['days_to_show'] = selected_days
        context['allowed_day_filters'] = self.allowed_day_filters
        return context


class AdminAppointmentCreateView(SuperAdminAndAdminOnlyMixin, CreateView):
    """Create booking by admin/staff for patients in doctor hospital"""
    model = PatientAppointment
    form_class = AdminAppointmentBookingForm
    template_name = 'appointments/appointment_admin_form.html'
    slot_window_days = 14

    def get_success_url(self):
        return reverse_lazy('appointments:appointment_doctor_schedule', kwargs={'pk': self.get_doctor().pk})

    def get_doctor(self):
        doctor_id = self.kwargs.get('doctor_id')
        return get_object_or_404(Doctor, id=doctor_id, is_available=True, is_active=True)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.get_doctor().hospital
        
        # Pre-populate form data with date/time from URL parameters
        if self.request.method == 'GET':
            initial_data = {}
            date_param = self.request.GET.get('date', '').strip()
            time_param = self.request.GET.get('time', '').strip()
            
            if date_param:
                initial_data['appointment_date'] = date_param
            if time_param:
                initial_data['appointment_time'] = time_param
            
            if initial_data:
                kwargs['initial'] = initial_data
        
        return kwargs


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.get_doctor()
        
        # Get date and time from URL parameters or form data
        appointment_date = self.request.POST.get('appointment_date') or self.request.GET.get('date', '')
        appointment_time = self.request.POST.get('appointment_time') or self.request.GET.get('time', '')
        
        # Parse date
        if appointment_date:
            try:
                if isinstance(appointment_date, str):
                    appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                appointment_date = None
        
        # Parse time
        if appointment_time:
            try:
                if isinstance(appointment_time, str):
                    appointment_time = datetime.strptime(appointment_time, '%H:%M').time()
            except (ValueError, TypeError):
                appointment_time = None
        
    
        context['doctor'] = doctor
        context['doctor_full_name'] = f"Dr. {doctor.user.get_full_name()}"
        context['appointment_date'] = appointment_date
        context['appointment_time'] = appointment_time
        return context

    def form_valid(self, form):
        doctor = self.get_doctor()
        patient = form.cleaned_data.get('patient')
        appointment_date = form.cleaned_data.get('appointment_date')
        appointment_time = form.cleaned_data.get('appointment_time')

        # Check for existing active booking
        if has_existing_active_booking(patient=patient, doctor=doctor):
            form.add_error(
                'appointment_time',
                'This patient already has an active booking with this doctor. Complete or cancel it before booking again.',
            )
            return self.form_invalid(form)

        # Verify doctor has schedule for this time
        weekday = appointment_date.weekday()
        schedule = doctor.schedules.filter(
            weekday=weekday,
            is_available=True,
            start_time=appointment_time,
        ).first()

        if not schedule:
            form.add_error('appointment_time', 'Doctor is not available at this selected day/time.')
            return self.form_invalid(form)

        # Check slot availability
        existing_appointments = PatientAppointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time__gte=schedule.start_time,
            appointment_time__lte=schedule.end_time,
            status__in=ACTIVE_BOOKING_STATUSES
        ).count()

        if existing_appointments >= schedule.max_patients:
            form.add_error('appointment_time', 'This time slot is fully booked.')
            return self.form_invalid(form)

        # Create appointment
        appointment = form.save(commit=False)
        appointment.patient = patient
        appointment.doctor = doctor
        appointment.hospital = doctor.hospital
        appointment.status = get_booking_status(
            patient=patient,
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            default_status='SCHEDULED',
        )
        appointment.is_follow_up = appointment.status == 'FOLLOW_UP'
        appointment.save()

        # Create payment record
        appointment_fee = 10 if appointment.status == 'FOLLOW_UP' else doctor.consultation_fee
        AppointmentPayment.objects.get_or_create(
            appointment=appointment,
            defaults={
                'amount': appointment_fee,
                'status': AppointmentPayment.PaymentStatus.PENDING,
                'payment_method': AppointmentPayment.PaymentMethod.CASH,
            },
        )

        messages.success(
            self.request,
            f'Appointment booked for {patient.user.get_full_name() or patient.user.username}.',
        )
        return redirect('payments:appointment_payment', appointment_id=appointment.id)


class AdminAppointmentListView(SuperAdminAndAdminOnlyMixin, ListView):
    """List appointments for admin/super-admin with basic filters."""
    model = PatientAppointment
    template_name = 'appointments/appointment_list.html'
    context_object_name = 'appointments'
    paginate_by = 20

    def get_queryset(self):
        queryset = PatientAppointment.objects.select_related(
            'patient__user',
            'doctor__user',
            'doctor__hospital',
            'payment',
        ).order_by('-appointment_date', '-appointment_time')

        status = self.request.GET.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)

        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(patient__user__first_name__icontains=search)
                | Q(patient__user__last_name__icontains=search)
                | Q(patient__booking_uuid__icontains=search)
                | Q(doctor__user__first_name__icontains=search)
                | Q(doctor__user__last_name__icontains=search)
                | Q(doctor__hospital__name__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_status'] = self.request.GET.get('status', '').strip()
        context['search_query'] = self.request.GET.get('search', '').strip()
        context['status_choices'] = PatientAppointment.STATUS_CHOICES
        return context


class AdminAppointmentDetailView(SuperAdminAndAdminOnlyMixin, DetailView):
    """Show appointment detail for admin/super-admin."""
    model = PatientAppointment
    template_name = 'appointments/appointment_manage_detail.html'
    context_object_name = 'appointment'

    def get_queryset(self):
        return PatientAppointment.objects.select_related(
            'patient__user',
            'doctor__user',
            'doctor__hospital',
            'payment',
        )


class AdminAppointmentUpdateView(SuperAdminAndAdminOnlyMixin, UpdateView):
    """Edit appointment for admin/super-admin."""
    model = PatientAppointment
    form_class = AppointmentEditForm
    template_name = 'appointments/appointment_manage_form.html'
    context_object_name = 'appointment'

    def get_queryset(self):
        return PatientAppointment.objects.select_related(
            'patient__user',
            'doctor__user',
            'doctor__hospital',
        )

    def get_success_url(self):
        return reverse('appointments:appointment_manage_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Appointment updated successfully.')
        return super().form_valid(form)


class AdminAppointmentRescheduleView(SuperAdminAndAdminOnlyMixin, DetailView):
    """Allow admin/super-admin to reschedule appointments from manage panel."""
    model = PatientAppointment
    template_name = 'appointments/appointment_manage_reschedule.html'
    context_object_name = 'appointment'
    slot_window_days = 14

    def get_queryset(self):
        return PatientAppointment.objects.select_related(
            'patient__user',
            'doctor__user',
            'doctor__hospital',
            'payment',
        )

    def _is_slot_available(self, doctor, appointment_date, appointment_time, now):
        weekday = appointment_date.weekday()
        schedules = doctor.schedules.filter(
            weekday=weekday,
            is_available=True,
        ).order_by('start_time')

        if not schedules:
            return False

        for schedule in schedules:
            available_slot_times = {
                slot['time']
                for slot in schedule.get_available_slots(
                    appointment_date=appointment_date,
                    now=now,
                    active_statuses=ACTIVE_BOOKING_STATUSES,
                )
            }
            if appointment_time in available_slot_times:
                return True

        return False

    def _get_reschedule_window(self, appointment, now):
        start_date = max(appointment.appointment_date, now.date())
        end_date = start_date + timedelta(days=self.slot_window_days - 1)
        return start_date, end_date

    def _get_slots_window_now(self, appointment, now):
        start_date, _ = self._get_reschedule_window(appointment=appointment, now=now)
        if start_date == now.date():
            return now
        current_tz = timezone.get_current_timezone()
        return timezone.make_aware(datetime.combine(start_date, datetime.min.time()), current_tz)

    def post(self, request, *args, **kwargs):
        appointment = self.get_object()

        if appointment.status in ['COMPLETED', 'CANCELLED']:
            messages.error(request, 'Completed or cancelled appointments cannot be rescheduled.')
            return redirect('appointments:appointment_manage_detail', pk=appointment.pk)

        if not appointment.doctor:
            messages.error(request, 'This appointment has no assigned doctor and cannot be rescheduled.')
            return redirect('appointments:appointment_manage_detail', pk=appointment.pk)

        appointment_date_str = request.POST.get('appointment_date', '').strip()
        appointment_time_str = request.POST.get('appointment_time', '').strip()

        try:
            appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
            appointment_time = datetime.strptime(appointment_time_str, '%H:%M').time()
        except (ValueError, TypeError):
            messages.error(request, 'Invalid date/time selected. Please choose an available slot.')
            return redirect('appointments:appointment_manage_reschedule', pk=appointment.pk)

        now = timezone.now()
        selected_dt = timezone.make_aware(datetime.combine(appointment_date, appointment_time))
        if selected_dt <= now:
            messages.error(request, 'Please choose a future time slot.')
            return redirect('appointments:appointment_manage_reschedule', pk=appointment.pk)

        window_start_date, window_end_date = self._get_reschedule_window(appointment=appointment, now=now)
        if appointment_date < window_start_date or appointment_date > window_end_date:
            messages.error(
                request,
                f'Please choose a date between {window_start_date:%Y-%m-%d} and {window_end_date:%Y-%m-%d}.',
            )
            return redirect('appointments:appointment_manage_reschedule', pk=appointment.pk)

        slot_is_available = self._is_slot_available(
            doctor=appointment.doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            now=now,
        )

        if not slot_is_available:
            messages.error(request, 'Selected slot is no longer available. Please select another slot.')
            return redirect('appointments:appointment_manage_reschedule', pk=appointment.pk)

        appointment.appointment_date = appointment_date
        appointment.appointment_time = appointment_time
        appointment.status = 'RESCHEDULED'
        appointment.save(update_fields=['appointment_date', 'appointment_time', 'status', 'modified'])

        messages.success(request, 'Appointment rescheduled successfully.')
        return redirect('appointments:appointment_manage_detail', pk=appointment.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment = self.object

        if appointment.status in ['COMPLETED', 'CANCELLED']:
            context['available_slots'] = []
            context['can_reschedule'] = False
            context['doctor_full_name'] = (
                f"Dr. {appointment.doctor.user.get_full_name()}"
                if appointment.doctor and appointment.doctor.user
                else 'Doctor'
            )
            return context

        doctor = appointment.doctor
        if not doctor:
            context['available_slots'] = []
            context['can_reschedule'] = False
            context['doctor_full_name'] = 'Doctor'
            return context

        context['available_slots'] = doctor.get_available_slots_by_date(
            days=self.slot_window_days,
            now=self._get_slots_window_now(appointment=appointment, now=timezone.now()),
            active_statuses=ACTIVE_BOOKING_STATUSES,
        )
        context['doctor_full_name'] = f"Dr. {doctor.user.get_full_name()}"
        context['can_reschedule'] = True
        context['selected_date'] = self.request.GET.get('date', '').strip()
        context['selected_time'] = self.request.GET.get('time', '').strip()
        return context