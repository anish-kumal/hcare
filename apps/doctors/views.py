from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.dateparse import parse_time
from django.utils.html import strip_tags
from django.views.generic import TemplateView
from django.core.exceptions import PermissionDenied

from .models import Doctor, DoctorSchedule
from .forms import DoctorUserForm, DoctorProfileForm, DoctorUserUpdateForm
from apps.hospitals.models import Hospital, HospitalAdmin
from apps.base.mixin import SuperAdminAndAdminOnlyMixin

User = get_user_model()


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
		doctor = Doctor.objects.filter(user=self.request.user).first()
		context['doctor'] = doctor
		return context

	def post(self, request, *args, **kwargs):
		doctor = Doctor.objects.filter(user=request.user).first()
		if not doctor:
			messages.error(request, 'Doctor profile not found.')
			return redirect('doctor_dashboard')

		first_name = request.POST.get('first_name', '').strip()
		last_name = request.POST.get('last_name', '').strip()
		email = request.POST.get('email', '').strip()
		phone_number = request.POST.get('phone_number', '').strip()
		specialization = request.POST.get('specialization', '').strip()

		if not email:
			messages.error(request, 'Email is required.')
			return redirect('doctors:doctor_profile')

		request.user.first_name = first_name
		request.user.last_name = last_name
		request.user.email = email
		request.user.phone_number = phone_number

		if specialization:
			doctor.specialization = specialization

		try:
			request.user.save()
			doctor.save()
		except IntegrityError:
			messages.error(request, 'Email is already in use. Please choose another.')
			return redirect('doctors:doctor_profile')

		messages.success(request, 'Profile updated successfully.')
		return redirect('doctors:doctor_profile')


class DoctorCreateView(LoginRequiredMixin, TemplateView):
	"""
	Create Doctor - Both User and Doctor Profile in one page
	Hospital Admin can create doctors for their hospital
	Super Admin can create doctors for any hospital
	"""
	template_name = 'doctors/doctor_create.html'
	login_url = 'users:login'
	
	def dispatch(self, request, *args, **kwargs):
		"""Check if user has permission to create doctors"""
		if not request.user.is_authenticated:
			return self.handle_no_permission()
		
		# Only super admin and hospital admin can create doctors
		if not (request.user.is_super_admin or request.user.is_admin):
			messages.error(request, 'You do not have permission to create doctors.')
			raise PermissionDenied
		
		return super().dispatch(request, *args, **kwargs)
	
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		user_form = kwargs.get('user_form') or DoctorUserForm()
		doctor_form = kwargs.get('doctor_form') or DoctorProfileForm()
		
		context['user_form'] = user_form
		context['doctor_form'] = doctor_form
		
		# Get hospitals based on user type
		if self.request.user.is_super_admin:
			context['hospitals'] = Hospital.objects.all().order_by('name')
		elif self.request.user.is_admin:
			# Hospital admin can only see their own hospital
			hospital_admin = HospitalAdmin.objects.filter(user=self.request.user).first()
			if hospital_admin:
				context['hospitals'] = Hospital.objects.filter(id=hospital_admin.hospital.id)
				context['hospital_id'] = hospital_admin.hospital.id
		
		return context
	
	def post(self, request, *args, **kwargs):
		"""Handle doctor creation"""
		# Validate hospital selection
		hospital_id = request.POST.get('hospital')
		if not hospital_id:
			messages.error(request, 'Please select a hospital.')
			return self.get(request, *args, **kwargs)
		
		try:
			hospital_id = int(hospital_id)
			hospital = Hospital.objects.get(id=hospital_id)
		except (ValueError, Hospital.DoesNotExist):
			messages.error(request, 'Selected hospital does not exist.')
			return self.get(request, *args, **kwargs)
		
		# Validate hospital admin permissions
		if request.user.is_admin:
			hospital_admin = HospitalAdmin.objects.filter(user=request.user).first()
			if not hospital_admin or hospital_admin.hospital.id != hospital.id:
				messages.error(request, 'You can only create doctors for your hospital.')
				raise PermissionDenied
		
		# Create forms
		user_form = DoctorUserForm(request.POST)
		doctor_form = DoctorProfileForm(request.POST, request.FILES)
		
		# Validate both forms
		if user_form.is_valid() and doctor_form.is_valid():
			try:
				with transaction.atomic():
					# 1. Save User first
					user = user_form.save(commit=False)
					user.user_type = User.UserType.DOCTOR
					user.is_default_password = True
					user.save()
					
					# Set password
					password = user_form.cleaned_data.get('password')
					user.set_password(password)
					user.save()
					
					# 2. Save Doctor Profile
					doctor = doctor_form.save(commit=False)
					doctor.user = user
					doctor.hospital = hospital
					doctor.save()


				next_response = redirect('doctors:doctor_list')


				if password:
					login_url = self.request.build_absolute_uri(reverse_lazy('users:administer_login'))
					context = {
						'title': 'Your doctor account for ',
						'user_name': user.get_full_name() or user.username,
						'hospital_name': hospital.name,
						'username': user.username,
						'password': password,
						'login_url': login_url,
						'support_email': settings.DEFAULT_FROM_EMAIL,
					}

					try:
						html_message = render_to_string('email/credentials_email.html', context)
						plain_message = strip_tags(html_message)
						send_mail(
							subject='Your Doctor Login Credentials',
							message=plain_message,
							from_email=settings.DEFAULT_FROM_EMAIL,
							recipient_list=[user.email],
							html_message=html_message,
							fail_silently=False,
						)
						messages.success(request, 'Doctor created successfully! Credentials email sent.')
					except Exception:
						messages.warning(
							request,
							'Doctor created successfully, but credential email could not be sent. Please share credentials manually.'
						)
				else:
					messages.success(request, f'Doctor {user.get_full_name()} has been created successfully!')

				return next_response
			
			except IntegrityError as e:
				messages.error(request, f'Error creating doctor: {str(e)}')
				return self.get(
					request, 
					user_form=user_form, 
					doctor_form=doctor_form,
					*args, 
					**kwargs
				)
		else:
			# Forms not valid, return with errors
			messages.error(request, 'Please correct the errors below.')
			return self.get(
				request, 
				user_form=user_form, 
				doctor_form=doctor_form,
				*args, 
				**kwargs
			)


class DoctorListView(SuperAdminAndAdminOnlyMixin, TemplateView):
	"""List doctors for admins"""
	template_name = 'doctors/doctor_list.html'

	def get_queryset(self):
		queryset = Doctor.objects.select_related('user', 'hospital', 'department').order_by('-created')

		if self.request.user.is_admin:
			hospital_admin = HospitalAdmin.objects.filter(user=self.request.user).select_related('hospital').first()
			if not hospital_admin:
				return Doctor.objects.none()
			queryset = queryset.filter(hospital=hospital_admin.hospital)

		search_query = self.request.GET.get('search', '').strip()
		if search_query:
			queryset = queryset.filter(
				Q(user__first_name__icontains=search_query)
				| Q(user__last_name__icontains=search_query)
				| Q(user__username__icontains=search_query)
				| Q(user__email__icontains=search_query)
				| Q(specialization__icontains=search_query)
				| Q(license_number__icontains=search_query)
			)

		return queryset

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['doctors'] = self.get_queryset()
		context['search_query'] = self.request.GET.get('search', '').strip()
		return context


class DoctorDetailView(SuperAdminAndAdminOnlyMixin, TemplateView):
	"""Doctor detail view for admins"""
	template_name = 'doctors/doctor_detail.html'

	def get_doctor(self):
		doctor = get_object_or_404(
			Doctor.objects.select_related('user', 'hospital', 'department'),
			pk=self.kwargs.get('pk'),
		)

		if self.request.user.is_admin:
			hospital_admin = HospitalAdmin.objects.filter(user=self.request.user).select_related('hospital').first()
			if not hospital_admin or doctor.hospital_id != hospital_admin.hospital_id:
				raise PermissionDenied

		return doctor

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['doctor'] = self.get_doctor()
		return context


class DoctorDeleteView(SuperAdminAndAdminOnlyMixin, TemplateView):
	"""Delete doctor user and profile"""
	template_name = 'partials/delete.html'

	def get_doctor(self):
		doctor = get_object_or_404(
			Doctor.objects.select_related('user', 'hospital'),
			pk=self.kwargs.get('pk'),
		)

		if self.request.user.is_admin:
			hospital_admin = HospitalAdmin.objects.filter(user=self.request.user).select_related('hospital').first()
			if not hospital_admin or doctor.hospital_id != hospital_admin.hospital_id:
				raise PermissionDenied

		return doctor

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		doctor = self.get_doctor()
		context.update({
			'doctor': doctor,
			'delete_page_title': 'Delete Doctor - Health Care',
			'delete_confirm_title': 'Delete Doctor?',
			'delete_confirm_message': (
				f'Are you sure you want to delete Dr. {doctor.user.get_full_name() or doctor.user.username}? '
				'This action cannot be undone.'
			),
			'delete_warning_text': (
				'Deleting this doctor will remove the doctor profile and login account permanently.'
			),
			'delete_button_label': 'Delete Doctor',
			'cancel_url': self.request.META.get('HTTP_REFERER') or '/doctors/',
		})
		return context

	def post(self, request, *args, **kwargs):
		doctor = self.get_doctor()
		doctor_name = doctor.user.get_full_name() or doctor.user.username

		try:
			with transaction.atomic():
				doctor.user.delete()
			messages.success(request, f'Doctor {doctor_name} deleted successfully.')
		except IntegrityError as exc:
			messages.error(request, f'Could not delete doctor: {exc}')
			return redirect('doctors:doctor_detail', pk=doctor.pk)

		return redirect('doctors:doctor_list')


class DoctorUpdateView(SuperAdminAndAdminOnlyMixin, TemplateView):
	"""Update doctor user and profile details"""
	template_name = 'doctors/doctor_edit.html'

	def get_doctor(self):
		doctor = get_object_or_404(
			Doctor.objects.select_related('user', 'hospital', 'department'),
			pk=self.kwargs.get('pk'),
		)

		if self.request.user.is_admin:
			hospital_admin = HospitalAdmin.objects.filter(user=self.request.user).select_related('hospital').first()
			if not hospital_admin or doctor.hospital_id != hospital_admin.hospital_id:
				raise PermissionDenied

		return doctor

	def get_hospitals(self):
		if self.request.user.is_super_admin:
			return Hospital.objects.all().order_by('name')

		hospital_admin = HospitalAdmin.objects.filter(user=self.request.user).select_related('hospital').first()
		if hospital_admin:
			return Hospital.objects.filter(id=hospital_admin.hospital_id)

		return Hospital.objects.none()

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		doctor = kwargs.get('doctor') or self.get_doctor()
		user_form = kwargs.get('user_form') or DoctorUserUpdateForm(instance=doctor.user)
		doctor_form = kwargs.get('doctor_form') or DoctorProfileForm(instance=doctor)

		context['doctor'] = doctor
		context['user_form'] = user_form
		context['doctor_form'] = doctor_form
		context['hospitals'] = self.get_hospitals()
		context['hospital_id'] = doctor.hospital_id
		return context

	def post(self, request, *args, **kwargs):
		doctor = self.get_doctor()

		if request.user.is_super_admin:
			hospital_id = request.POST.get('hospital')
			if not hospital_id:
				messages.error(request, 'Please select a hospital.')
				return self.get(request, doctor=doctor, *args, **kwargs)
			hospital = get_object_or_404(Hospital, id=hospital_id)
		else:
			hospital_admin = HospitalAdmin.objects.filter(user=request.user).select_related('hospital').first()
			if not hospital_admin:
				messages.error(request, 'You are not assigned to any hospital.')
				return redirect('doctors:doctor_list')
			hospital = hospital_admin.hospital

		user_form = DoctorUserUpdateForm(request.POST, instance=doctor.user)
		doctor_form = DoctorProfileForm(request.POST, request.FILES, instance=doctor)

		if user_form.is_valid() and doctor_form.is_valid():
			try:
				with transaction.atomic():
					user_form.save()
					updated_doctor = doctor_form.save(commit=False)
					updated_doctor.hospital = hospital
					updated_doctor.save()

				messages.success(request, 'Doctor updated successfully.')
				return redirect('doctors:doctor_list')
			except IntegrityError as exc:
				messages.error(request, f'Error updating doctor: {exc}')

		messages.error(request, 'Please correct the errors below.')
		return self.get(
			request,
			doctor=doctor,
			user_form=user_form,
			doctor_form=doctor_form,
			*args,
			**kwargs,
		)


