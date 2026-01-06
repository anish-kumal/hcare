from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.shortcuts import redirect
from django.utils.dateparse import parse_time
from django.views.generic import TemplateView

from .models import Doctor, DoctorSchedule, Specialization


class DoctorOnlyMixin(LoginRequiredMixin):
	"""Restrict views to doctor users only"""
	login_url = 'users:login'

	def dispatch(self, request, *args, **kwargs):
		if not request.user.is_authenticated:
			return self.handle_no_permission()
		if not request.user.is_doctor:
			messages.error(request, 'You do not have permission to access this page.')
			return redirect('index')
		return super().dispatch(request, *args, **kwargs)


class DoctorScheduleListView(DoctorOnlyMixin, TemplateView):
	"""List doctor schedules"""
	template_name = 'doctor/schedule_list.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		doctor = Doctor.objects.filter(user=self.request.user).first()
		context['doctor'] = doctor
		context['schedules'] = DoctorSchedule.objects.filter(doctor=doctor).order_by('weekday', 'start_time') if doctor else []
		return context


class DoctorScheduleCreateView(DoctorOnlyMixin, TemplateView):
	"""Create doctor schedule"""
	template_name = 'doctor/schedule_form.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		doctor = Doctor.objects.filter(user=self.request.user).first()
		context['doctor'] = doctor
		context['weekday_choices'] = DoctorSchedule.WEEKDAY_CHOICES
		return context

	def post(self, request, *args, **kwargs):
		doctor = Doctor.objects.filter(user=request.user).first()
		if not doctor:
			messages.error(request, 'Doctor profile not found.')
			return redirect('doctor_dashboard')

		schedule_data = self._extract_schedule_data(request)
		if schedule_data is None:
			return redirect('doctors:doctor_schedule_create')

		try:
			DoctorSchedule.objects.update_or_create(
				doctor=doctor,
				weekday=schedule_data['weekday'],
				start_time=schedule_data['start_time'],
				defaults={
					'end_time': schedule_data['end_time'],
					'slot_duration': schedule_data['slot_duration'],
					'max_patients': schedule_data['max_patients'],
					'is_available': schedule_data['is_available'],
				}
			)
		except IntegrityError:
			messages.error(request, 'A schedule already exists for that day and start time.')
			return redirect('doctors:doctor_schedule_create')

		messages.success(request, 'Schedule created successfully.')
		return redirect('doctors:doctor_schedule_list')

	def _extract_schedule_data(self, request):
		weekday_raw = request.POST.get('weekday', '').strip()
		start_time_raw = request.POST.get('start_time', '').strip()
		end_time_raw = request.POST.get('end_time', '').strip()
		slot_duration_raw = request.POST.get('slot_duration', '').strip()
		max_patients_raw = request.POST.get('max_patients', '').strip()
		is_available = request.POST.get('is_available') == 'on'

		try:
			weekday = int(weekday_raw)
		except ValueError:
			messages.error(request, 'Please select a valid weekday.')
			return None

		start_time = parse_time(start_time_raw)
		end_time = parse_time(end_time_raw)

		if not start_time or not end_time:
			messages.error(request, 'Start time and end time are required.')
			return None

		if end_time <= start_time:
			messages.error(request, 'End time must be later than start time.')
			return None

		try:
			slot_duration = int(slot_duration_raw) if slot_duration_raw else 30
			max_patients = int(max_patients_raw) if max_patients_raw else 20
		except ValueError:
			messages.error(request, 'Slot duration and max patients must be valid numbers.')
			return None

		if slot_duration <= 0 or max_patients <= 0:
			messages.error(request, 'Slot duration and max patients must be greater than zero.')
			return None

		return {
			'weekday': weekday,
			'start_time': start_time,
			'end_time': end_time,
			'slot_duration': slot_duration,
			'max_patients': max_patients,
			'is_available': is_available,
		}


class DoctorScheduleDetailView(DoctorOnlyMixin, TemplateView):
	"""Schedule detail view"""
	template_name = 'doctor/schedule_detail.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		doctor = Doctor.objects.filter(user=self.request.user).first()
		schedule = DoctorSchedule.objects.filter(doctor=doctor, pk=kwargs.get('pk')).first()
		if not schedule:
			messages.error(self.request, 'Schedule not found.')
			return context
		context['doctor'] = doctor
		context['schedule'] = schedule
		return context


class DoctorScheduleUpdateView(DoctorOnlyMixin, TemplateView):
	"""Edit doctor schedule"""
	template_name = 'doctor/schedule_edit.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		doctor = Doctor.objects.filter(user=self.request.user).first()
		schedule = DoctorSchedule.objects.filter(doctor=doctor, pk=kwargs.get('pk')).first()
		if not schedule:
			messages.error(self.request, 'Schedule not found.')
			return context
		context['doctor'] = doctor
		context['schedule'] = schedule
		context['weekday_choices'] = DoctorSchedule.WEEKDAY_CHOICES
		return context

	def post(self, request, *args, **kwargs):
		doctor = Doctor.objects.filter(user=request.user).first()
		schedule = DoctorSchedule.objects.filter(doctor=doctor, pk=kwargs.get('pk')).first()
		if not schedule:
			messages.error(request, 'Schedule not found.')
			return redirect('doctors:doctor_schedule_list')

		schedule_data = DoctorScheduleCreateView()._extract_schedule_data(request)
		if schedule_data is None:
			return redirect('doctors:doctor_schedule_edit', pk=schedule.pk)

		schedule.weekday = schedule_data['weekday']
		schedule.start_time = schedule_data['start_time']
		schedule.end_time = schedule_data['end_time']
		schedule.slot_duration = schedule_data['slot_duration']
		schedule.max_patients = schedule_data['max_patients']
		schedule.is_available = schedule_data['is_available']

		try:
			schedule.save()
		except IntegrityError:
			messages.error(request, 'Another schedule already exists for that day and start time.')
			return redirect('doctors:doctor_schedule_edit', pk=schedule.pk)

		messages.success(request, 'Schedule updated successfully.')
		return redirect('doctors:doctor_schedule_detail', pk=schedule.pk)


class DoctorProfileEditView(DoctorOnlyMixin, TemplateView):
	"""Doctor profile edit"""
	template_name = 'doctor/profile_form.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		doctor = Doctor.objects.filter(user=self.request.user).select_related('specialization').first()
		context['doctor'] = doctor
		context['specializations'] = Specialization.objects.order_by('name')
		return context

	def post(self, request, *args, **kwargs):
		doctor = Doctor.objects.filter(user=request.user).select_related('specialization').first()
		if not doctor:
			messages.error(request, 'Doctor profile not found.')
			return redirect('doctor_dashboard')

		first_name = request.POST.get('first_name', '').strip()
		last_name = request.POST.get('last_name', '').strip()
		email = request.POST.get('email', '').strip()
		phone_number = request.POST.get('phone_number', '').strip()
		specialization_id = request.POST.get('specialization_id', '').strip()

		if not email:
			messages.error(request, 'Email is required.')
			return redirect('doctors:doctor_profile')

		request.user.first_name = first_name
		request.user.last_name = last_name
		request.user.email = email
		request.user.phone_number = phone_number

		if specialization_id:
			specialization = Specialization.objects.filter(id=specialization_id).first()
			if not specialization:
				messages.error(request, 'Please select a valid specialization.')
				return redirect('doctors:doctor_profile')
			doctor.specialization = specialization

		try:
			request.user.save()
			doctor.save()
		except IntegrityError:
			messages.error(request, 'Email is already in use. Please choose another.')
			return redirect('doctors:doctor_profile')

		messages.success(request, 'Profile updated successfully.')
		return redirect('doctors:doctor_profile')
