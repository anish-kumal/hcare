from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import datetime, timedelta

from apps.doctors.models import Doctor
from apps.patients.models import Patient, PatientAppointment
from .forms import AppointmentBookingForm, AppointmentEditForm
from apps.base.mixin import RoleRequiredMixin, SuperAdminAndAdminOnlyMixin





class DoctorListView(RoleRequiredMixin, ListView):
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


class DoctorDetailView(RoleRequiredMixin, DetailView):
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
                    status__in=['SCHEDULED', 'CONFIRMED']
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


class AppointmentCreateView(LoginRequiredMixin, CreateView):
    """Create an appointment booking"""
    model = PatientAppointment
    form_class = AppointmentBookingForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('appointments:booking_confirmation')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if patient profile exists"""
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in first to continue.')
            return self.handle_no_permission()

        try:
            Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            messages.error(request, 'Please complete your patient profile before booking an appointment.')
            return redirect('patient_dashboard')
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
            status__in=['SCHEDULED', 'CONFIRMED']
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
        appointment.status = 'SCHEDULED'
        appointment.save()
        
        messages.success(self.request, 'Appointment booked successfully!')
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        """Handle invalid form"""
        return self.render_to_response(self.get_context_data(form=form))


class BookingConfirmationView(LoginRequiredMixin, ListView):
    """Show recent bookings and confirmation"""
    template_name = 'appointments/booking_confirmation.html'
    context_object_name = 'appointments'
    
    def dispatch(self, request, *args, **kwargs):
        """Check if patient profile exists"""
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in first to continue.')
            return self.handle_no_permission()

        try:
            Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            messages.error(request, 'Please complete your patient profile before viewing appointments.')
            return redirect('patient_dashboard')
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
            status__in=['SCHEDULED', 'CONFIRMED']
        ).select_related('doctor', 'doctor__user').order_by('appointment_date', 'appointment_time')
        
        # Get past appointments
        context['past_appointments'] = PatientAppointment.objects.filter(
            patient=patient,
            appointment_date__lt=timezone.now().date()
        ).select_related('doctor', 'doctor__user').order_by('-appointment_date', '-appointment_time')
        
        return context


class AppointmentDetailView(LoginRequiredMixin, DetailView):
    """View appointment details and edit appointment"""
    model = PatientAppointment
    template_name = 'appointments/appointment_detail.html'
    context_object_name = 'appointment'
    
    def get_queryset(self):
        """Only show appointments for the current patient"""
        patient = Patient.objects.get(user=self.request.user)
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
    booking_statuses = ['SCHEDULED', 'CONFIRMED', 'IN_PROGRESS']
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