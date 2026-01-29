from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from datetime import datetime, timedelta

from apps.doctors.models import Doctor
from apps.patients.models import Patient, PatientAppointment
from apps.payments.models import AppointmentPayment
from .forms import AppointmentBookingForm, AppointmentEditForm, AdminAppointmentBookingForm
from apps.base.mixin import SuperAdminAndAdminOnlyMixin


ACTIVE_BOOKING_STATUSES = ['SCHEDULED', 'FOLLOW_UP']


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
    """Set follow-up when latest previous CONFIRMED booking for same doctor is within 7 days."""
    previous_confirmed_appointment = PatientAppointment.objects.filter(
        patient=patient,
        doctor=doctor,
        status='CONFIRMED',
    ).filter(
        Q(appointment_date__lt=appointment_date)
        | Q(appointment_date=appointment_date, appointment_time__lt=appointment_time)
    ).order_by('-appointment_date', '-appointment_time').first()

    if not previous_confirmed_appointment:
        return default_status

    current_dt = timezone.make_aware(datetime.combine(appointment_date, appointment_time))
    previous_dt = timezone.make_aware(
        datetime.combine(
            previous_confirmed_appointment.appointment_date,
            previous_confirmed_appointment.appointment_time,
        )
    )

    if current_dt - previous_dt <= timedelta(days=7):
        return 'FOLLOW_UP'

    return default_status





class DoctorListView(PatientAccessMixin, ListView):
    """List all available doctors for booking"""
    template_name = 'appointments/doctor_list.html'
    context_object_name = 'doctors'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Doctor.objects.filter(
            is_available=True,
            is_active=True
        ).select_related('user', 'hospital').prefetch_related('schedules')
        
        # Filter by specialization if provided
        specialization_id = self.request.GET.get('specialization')
        if specialization_id:
            queryset = queryset.filter(specialization=specialization_id)
        
        # Filter by search query
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                user__first_name__icontains=search_query
            ) | queryset.filter(
                user__last_name__icontains=search_query
            ) | queryset.filter(
                specialization__icontains=search_query
            )
        
        return queryset.order_by('user__first_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get unique specialization values (CharField), filter out empty ones
        specs = Doctor.objects.filter(
            specialization__isnull=False
        ).exclude(
            specialization=''
        ).values_list('specialization', flat=True).distinct().order_by('specialization')
        context['specializations'] = specs
        context['selected_specialization'] = self.request.GET.get('specialization')
        context['search_query'] = self.request.GET.get('q')
        return context


class DoctorDetailView(PatientAccessMixin, DetailView):
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
        
        # Get available appointment slots for the next 7 days
        available_slots = []
        today = timezone.now().date()
        now = timezone.now()
        
        for i in range(7):
            appointment_date = today + timedelta(days=i)
            weekday = appointment_date.weekday()
            
            # Get schedule for this day
            schedule = doctor.schedules.filter(weekday=weekday, is_available=True).first()
            
            if schedule:
                # Generate time slots based on slot duration
                slots = []
                current_time = datetime.combine(appointment_date, schedule.start_time)
                end_time = datetime.combine(appointment_date, schedule.end_time)
                
                # Count existing appointments for this slot
                existing_appointments = PatientAppointment.objects.filter(
                    doctor=doctor,
                    appointment_date=appointment_date,
                    status__in=ACTIVE_BOOKING_STATUSES
                ).count()
                
                if existing_appointments < schedule.max_patients:
                    while current_time < end_time:
                        slot_time = current_time.time()
                        # Make current_time timezone-aware for comparison
                        current_time_aware = timezone.make_aware(current_time)
                        
                        # Only include slots that are in the future (not past)
                        if current_time_aware > now:
                            slots.append({
                                'time': slot_time,
                                'datetime': current_time
                            })
                        current_time = current_time + timedelta(minutes=schedule.slot_duration)
                    
                    if slots:
                        available_slots.append({
                            'date': appointment_date,
                            'weekday': appointment_date.strftime('%A'),
                            'slots': slots,
                            'schedule': schedule
                        })
        
        context['available_slots'] = available_slots
        context['doctor_full_name'] = f"Dr. {doctor.user.get_full_name()}"
        return context


class AppointmentCreateView(PatientAccessMixin, CreateView):
    """Create an appointment booking"""
    model = PatientAppointment
    form_class = AppointmentBookingForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('appointments:booking_confirmation')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if patient profile exists"""
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
        
        # Get the schedule for this day
        weekday = appointment_date.weekday()
        schedule = doctor.schedules.filter(
            weekday=weekday,
            is_available=True
        ).first()
        
        if not schedule:
            messages.error(self.request, 'Doctor is not available on that day.')
            return self.form_invalid(form)
        
        # Check if time is within schedule
        if not (schedule.start_time <= appointment_time <= schedule.end_time):
            messages.error(self.request, 'Selected time is outside doctor\'s working hours.')
            return self.form_invalid(form)
        
        # Check if slot is available
        existing_appointments = PatientAppointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status__in=ACTIVE_BOOKING_STATUSES
        ).count()
        
        if existing_appointments >= schedule.max_patients:
            messages.error(self.request, 'This time slot is fully booked. Please choose another time.')
            return self.form_invalid(form)
        
        # Create appointment
        appointment = form.save(commit=False)
        appointment.patient = patient
        appointment.doctor = doctor
        appointment.appointment_date = appointment_date
        appointment.appointment_time = appointment_time
        appointment.status = get_booking_status(
            patient=patient,
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            default_status='SCHEDULED',
        )
        appointment.save()

        AppointmentPayment.objects.get_or_create(
            appointment=appointment,
            defaults={
                'amount': doctor.consultation_fee,
                'status': AppointmentPayment.PaymentStatus.PENDING,
                'payment_method': AppointmentPayment.PaymentMethod.CASH,
            },
        )
        
        messages.success(self.request, 'Appointment booked successfully!')
        return redirect(self.success_url)
    
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
        ).select_related('doctor', 'doctor__user', 'doctor__hospital')
    
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
        context['doctor_full_name'] = f"Dr. {appointment.doctor.user.get_full_name()}"
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

                session_rows.append({
                    'schedule': schedule,
                    'booked_count': booked_count,
                    'slots_left': slots_left,
                    'bookings': session_bookings,
                })

            daily_max_patients = sum(session['schedule'].max_patients for session in session_rows)
            daily_booked_count = sum(session['booked_count'] for session in session_rows)

            weekly_schedule.append({
                'date': current_date,
                'weekday': current_date.strftime('%A'),
                'sessions': session_rows,
                'has_schedule': bool(day_schedules),
                'daily_max_patients': daily_max_patients,
                'daily_booked_count': daily_booked_count,
                'daily_slots_left': max(daily_max_patients - daily_booked_count, 0),
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
        return kwargs

    def get_available_slot_map(self, doctor):
        """Return available session start times keyed by date string (YYYY-MM-DD)."""
        today = timezone.now().date()
        now = timezone.now()

        schedules = doctor.schedules.filter(is_available=True).order_by('weekday', 'start_time')
        schedules_by_weekday = {}
        for schedule in schedules:
            schedules_by_weekday.setdefault(schedule.weekday, []).append(schedule)

        available_slot_map = {}
        for offset in range(self.slot_window_days):
            appointment_date = today + timedelta(days=offset)
            day_schedules = schedules_by_weekday.get(appointment_date.weekday(), [])
            if not day_schedules:
                continue

            day_slots = []
            for schedule in day_schedules:
                session_start_dt = timezone.make_aware(datetime.combine(appointment_date, schedule.start_time))
                if session_start_dt <= now:
                    continue

                booked_count = PatientAppointment.objects.filter(
                    doctor=doctor,
                    appointment_date=appointment_date,
                    appointment_time__gte=schedule.start_time,
                    appointment_time__lte=schedule.end_time,
                    status__in=ACTIVE_BOOKING_STATUSES,
                ).count()

                if booked_count < schedule.max_patients:
                    day_slots.append(schedule.start_time.strftime('%H:%M'))

            if day_slots:
                available_slot_map[appointment_date.strftime('%Y-%m-%d')] = sorted(set(day_slots))

        return available_slot_map

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.get_doctor()
        available_slot_map = self.get_available_slot_map(doctor)

        selected_date = self.request.POST.get('appointment_date') or self.request.GET.get('date', '')
        if selected_date not in available_slot_map:
            selected_date = next(iter(available_slot_map), '')

        date_slots = available_slot_map.get(selected_date, [])
        selected_time = self.request.POST.get('appointment_time') or self.request.GET.get('time', '')
        if selected_time not in date_slots:
            selected_time = date_slots[0] if date_slots else ''

        context['doctor'] = doctor
        context['doctor_full_name'] = f"Dr. {doctor.user.get_full_name()}"
        context['available_slot_map'] = available_slot_map
        context['available_dates'] = list(available_slot_map.keys())
        context['appointment_date'] = selected_date
        context['appointment_time'] = selected_time
        return context

    def form_valid(self, form):
        doctor = self.get_doctor()
        patient = form.cleaned_data.get('patient')

        appointment_date = form.cleaned_data.get('appointment_date')
        appointment_time = form.cleaned_data.get('appointment_time')

        available_slot_map = self.get_available_slot_map(doctor)
        date_key = appointment_date.strftime('%Y-%m-%d')
        time_key = appointment_time.strftime('%H:%M')
        if time_key not in available_slot_map.get(date_key, []):
            form.add_error('appointment_time', 'Please choose a valid available slot for this doctor.')
            return self.form_invalid(form)

        appointment_datetime = datetime.combine(appointment_date, appointment_time)
        appointment_datetime = timezone.make_aware(appointment_datetime)
        if appointment_datetime < timezone.now():
            form.add_error('appointment_time', 'Appointment date/time must be in the future.')
            return self.form_invalid(form)

        weekday = appointment_date.weekday()
        schedule = doctor.schedules.filter(
            weekday=weekday,
            is_available=True,
            start_time=appointment_time,
        ).first()

        if not schedule:
            form.add_error('appointment_time', 'Doctor is not available at this selected day/time.')
            return self.form_invalid(form)

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

        self.object = form.save(commit=False)
        self.object.patient = patient
        self.object.doctor = doctor
        self.object.status = get_booking_status(
            patient=patient,
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            default_status='SCHEDULED',
        )
        self.object.save()

        AppointmentPayment.objects.get_or_create(
            appointment=self.object,
            defaults={
                'amount': doctor.consultation_fee,
                'status': AppointmentPayment.PaymentStatus.PENDING,
                'payment_method': AppointmentPayment.PaymentMethod.CASH,
            },
        )

        messages.success(
            self.request,
            f'Appointment booked for {patient.user.get_full_name() or patient.user.username} with booking UUID {patient.booking_uuid}.',
        )
        return redirect('payments:appointment_payment', appointment_id=self.object.id)


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
