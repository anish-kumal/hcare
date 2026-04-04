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
from django.utils.html import strip_tags
from django.views.generic import CreateView, ListView, DetailView, UpdateView, DeleteView
from django.core.exceptions import PermissionDenied

from .models import Doctor, DoctorSchedule
from .forms import DoctorUserForm, DoctorProfileForm, DoctorUserUpdateForm, DoctorSelfProfileForm, DoctorScheduleForm
from apps.hospitals.models import Hospital, HospitalAdmin
from apps.patients.models import PatientAppointment
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


class DoctorScheduleListView(DoctorOnlyMixin, ListView):
	"""List doctor schedules"""
	template_name = 'doctor/schedule_list.html'
	context_object_name = 'schedules'

	def get_queryset(self):
		doctor = Doctor.objects.filter(user=self.request.user).first()
		if doctor:
			return DoctorSchedule.objects.filter(doctor=doctor).order_by('weekday', 'start_time')
		return DoctorSchedule.objects.none()

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['doctor'] = Doctor.objects.filter(user=self.request.user).first()
		return context


class DoctorScheduleCreateView(DoctorOnlyMixin, CreateView):
	"""Create doctor schedule"""
	model = DoctorSchedule
	form_class = DoctorScheduleForm
	template_name = 'doctor/schedule_form.html'
	success_url = reverse_lazy('doctors:doctor_schedule_list')

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['doctor'] = Doctor.objects.filter(user=self.request.user).first()
		return kwargs

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		doctor = Doctor.objects.filter(user=self.request.user).first()
		context['doctor'] = doctor
		context['weekday_choices'] = DoctorSchedule.WEEKDAY_CHOICES
		return context

	def form_valid(self, form):
		doctor = Doctor.objects.filter(user=self.request.user).first()
		if not doctor:
			messages.error(self.request, 'Doctor profile not found.')
			return redirect('doctor_dashboard')

		try:
			form.instance.doctor = doctor
			response = super().form_valid(form)
		except IntegrityError:
			messages.error(self.request, 'A schedule already exists for that day and start time.')
			return self.form_invalid(form)

		messages.success(self.request, 'Schedule created successfully.')
		return response


class DoctorScheduleDetailView(DoctorOnlyMixin, DetailView):
	"""Schedule detail view"""
	model = DoctorSchedule
	template_name = 'doctor/schedule_detail.html'
	context_object_name = 'schedule'

	def get_queryset(self):
		doctor = Doctor.objects.filter(user=self.request.user).first()
		if doctor:
			return DoctorSchedule.objects.filter(doctor=doctor)
		return DoctorSchedule.objects.none()

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['doctor'] = Doctor.objects.filter(user=self.request.user).first()
		return context


class DoctorScheduleUpdateView(DoctorOnlyMixin, UpdateView):
	"""Edit doctor schedule"""
	model = DoctorSchedule
	form_class = DoctorScheduleForm
	template_name = 'doctor/schedule_edit.html'
	context_object_name = 'schedule'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['doctor'] = Doctor.objects.filter(user=self.request.user).first()
		return kwargs

	def get_queryset(self):
		doctor = Doctor.objects.filter(user=self.request.user).first()
		return DoctorSchedule.objects.filter(doctor=doctor)

	def get_success_url(self):
		return reverse_lazy('doctors:doctor_schedule_detail', kwargs={'pk': self.object.pk})

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['doctor'] = Doctor.objects.filter(user=self.request.user).first()
		context['weekday_choices'] = DoctorSchedule.WEEKDAY_CHOICES
		return context

	def form_valid(self, form):
		try:
			return super().form_valid(form)
		except IntegrityError:
			messages.error(self.request, 'Another schedule already exists for that day and start time.')
			return self.form_invalid(form)

class DoctorScheduleDeleteView(DoctorOnlyMixin, DeleteView):
	"""Delete doctor schedule"""
	model = DoctorSchedule
	template_name = 'partials/delete.html'
	context_object_name = 'schedule'
	success_url = reverse_lazy('doctors:doctor_schedule_list')

	def get_queryset(self):
		doctor = Doctor.objects.filter(user=self.request.user).first()
		return DoctorSchedule.objects.filter(doctor=doctor)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		schedule = self.object
		context.update({
			'delete_page_title': 'Delete Schedule - Health Care',
			'delete_confirm_title': 'Delete Schedule Slot?',
			'delete_confirm_message': (
				f'Are you sure you want to delete your {schedule.get_weekday_display()} slot '
				f'({schedule.start_time.strftime("%H:%M")} - {schedule.end_time.strftime("%H:%M")})? '
				'This action cannot be undone.'
			),
			'delete_warning_text': (
				'Deleting this schedule slot will remove this availability from booking.'
			),
			'delete_button_label': 'Delete Schedule',
			'cancel_url': reverse_lazy('doctors:doctor_schedule_list'),
		})
		return context

	def form_valid(self, form):
		schedule = self.object
		slot_label = (
			f"{schedule.get_weekday_display()} "
			f"({schedule.start_time.strftime('%H:%M')} - {schedule.end_time.strftime('%H:%M')})"
		)
		response = super().form_valid(form)
		messages.success(self.request, f'Schedule slot {slot_label} deleted successfully.')
		return response
	


class DoctorProfileUpdateView(DoctorOnlyMixin, DetailView):
	"""Display doctor's current profile"""
	model = Doctor
	template_name = 'doctor/profile_detail.html'
	context_object_name = 'doctor'

	def get_object(self, queryset=None):
		return get_object_or_404(Doctor, user=self.request.user)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['user'] = self.request.user
		return context


class DoctorProfileEditView(DoctorOnlyMixin, UpdateView):
	"""Doctor profile edit - Display and update user and doctor info"""
	template_name = 'doctor/profile_form.html'
	model = Doctor
	form_class = DoctorSelfProfileForm
	success_url = reverse_lazy('doctors:doctor_profile')

	def get_object(self, queryset=None):
		"""Get the doctor profile for the current user"""
		return get_object_or_404(Doctor, user=self.request.user)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		doctor = self.object
		context['doctor_form'] = kwargs.get('doctor_form') or context.get('form')
		
		# Initialize user form - explicitly get from kwargs or create new one
		if 'user_form' in kwargs:
			context['user_form'] = kwargs['user_form']
		elif 'user_form' not in context:
			if self.request.method == 'POST':
				context['user_form'] = DoctorUserUpdateForm(self.request.POST, instance=doctor.user)
			else:
				context['user_form'] = DoctorUserUpdateForm(instance=doctor.user)
		
		context['doctor'] = doctor
		return context

	def post(self, request, *args, **kwargs):
		"""Handle updates for user and doctor profile details."""
		doctor = self.get_object()
		self.object = doctor  # Required by UpdateView/DetailMixin context handling on POST
		
		# Create forms
		user_form = DoctorUserUpdateForm(request.POST, instance=doctor.user)
		doctor_form = DoctorSelfProfileForm(request.POST, request.FILES, instance=doctor)
		
		# Validate both forms
		if user_form.is_valid() and doctor_form.is_valid():
			try:
				with transaction.atomic():
					# Update user
					user_form.save()
					
					# Update doctor profile
					doctor_form.save()
				
				messages.success(request, 'Profile updated successfully.')
				return redirect(self.success_url)
			
			except IntegrityError as exc:
				messages.error(request, f'Error updating profile: {exc}')
		else:
			messages.error(request, 'Please correct the errors below.')
		
		# Return form with errors
		return self.render_to_response(
			self.get_context_data(
				form=doctor_form,
				doctor_form=doctor_form,
				user_form=user_form,
			)
		)


		



class DoctorCreateView(LoginRequiredMixin, CreateView):
	"""
	Create Doctor - Both User and Doctor Profile in one page
	Hospital Admin can create doctors for their hospital
	Super Admin can create doctors for any hospital
	"""
	model = Doctor
	template_name = 'doctors/doctor_create.html'
	form_class = DoctorProfileForm
	success_url = reverse_lazy('doctors:doctor_list')
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
		doctor_form = kwargs.get('doctor_form') or context.get('form')
		
		context['user_form'] = user_form
		context['doctor_form'] = doctor_form
		context['selected_hospital_id'] = kwargs.get('hospital_id') or self.request.POST.get('hospital')
		
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
		self.object = None
		user_form = DoctorUserForm(request.POST)
		doctor_form = DoctorProfileForm(request.POST, request.FILES)
		selected_hospital_id = request.POST.get('hospital')

		# Validate forms first so field-level errors are preserved on any failure.
		forms_are_valid = user_form.is_valid() and doctor_form.is_valid()

		# Validate hospital selection
		if not selected_hospital_id:
			messages.error(request, 'Please select a hospital.')
			return self.render_to_response(
				self.get_context_data(
					user_form=user_form,
					doctor_form=doctor_form,
					hospital_id=selected_hospital_id,
				)
			)
		
		try:
			hospital_id = int(selected_hospital_id)
			hospital = Hospital.objects.get(id=hospital_id)
		except (ValueError, Hospital.DoesNotExist):
			messages.error(request, 'Selected hospital does not exist.')
			return self.render_to_response(
				self.get_context_data(
					user_form=user_form,
					doctor_form=doctor_form,
					hospital_id=selected_hospital_id,
				)
			)
		
		# Validate hospital admin permissions
		if request.user.is_admin:
			hospital_admin = HospitalAdmin.objects.filter(user=request.user).first()
			if not hospital_admin or hospital_admin.hospital.id != hospital.id:
				messages.error(request, 'You can only create doctors for your hospital.')
				raise PermissionDenied
		

		if forms_are_valid:
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
				return self.render_to_response(
					self.get_context_data(
						user_form=user_form,
						doctor_form=doctor_form,
						hospital_id=selected_hospital_id,
					)
				)
		else:
			# Forms not valid, return with errors
			messages.error(request, 'Please correct the highlighted errors below.')
			return self.render_to_response(
				self.get_context_data(
					user_form=user_form,
					doctor_form=doctor_form,
					hospital_id=selected_hospital_id,
				)
			)


class DoctorListView(SuperAdminAndAdminOnlyMixin, ListView):
	"""List doctors for admins"""
	model = Doctor
	template_name = 'doctors/doctor_list.html'
	context_object_name = 'doctors'

	def get_base_queryset(self):
		queryset = super().get_queryset().select_related('user', 'hospital', 'department').order_by('-created')

		if self.request.user.is_admin:
			hospital_admin = HospitalAdmin.objects.filter(user=self.request.user).select_related('hospital').first()
			if not hospital_admin:
				return Doctor.objects.none()
			queryset = queryset.filter(hospital=hospital_admin.hospital)

		return queryset

	def get_queryset(self):
		queryset = self.get_base_queryset()

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

		status_query = self.request.GET.get('status', '').strip().lower()
		if status_query == 'available':
			queryset = queryset.filter(is_available=True)
		elif status_query == 'unavailable':
			queryset = queryset.filter(is_available=False)

		return queryset

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['search_query'] = self.request.GET.get('search', '').strip()
		context['status_query'] = self.request.GET.get('status', '').strip().lower()

		base_queryset = self.get_base_queryset()
		context['total_doctors_count'] = base_queryset.count()
		context['available_doctors_count'] = base_queryset.filter(is_available=True).count()
		context['unavailable_doctors_count'] = base_queryset.filter(is_available=False).count()
		return context


class DoctorDetailView(SuperAdminAndAdminOnlyMixin, DetailView):
	"""Doctor detail view for admins"""
	model = Doctor
	template_name = 'doctors/doctor_detail.html'
	context_object_name = 'doctor'

	def get_queryset(self):
		return Doctor.objects.select_related('user', 'hospital', 'department')

	def get_object(self, queryset=None):
		obj = super().get_object(queryset)
		if self.request.user.is_admin:
			hospital_admin = HospitalAdmin.objects.filter(user=self.request.user).select_related('hospital').first()
			if not hospital_admin or obj.hospital_id != hospital_admin.hospital_id:
				raise PermissionDenied
		return obj


class DoctorDeleteView(SuperAdminAndAdminOnlyMixin, DeleteView):
	"""Delete doctor user and profile"""
	model = Doctor
	template_name = 'partials/delete.html'
	success_url = reverse_lazy('doctors:doctor_list')
	context_object_name = 'doctor'

	def get_queryset(self):
		return Doctor.objects.select_related('user', 'hospital')

	def get_object(self, queryset=None):
		obj = super().get_object(queryset)
		if self.request.user.is_admin:
			hospital_admin = HospitalAdmin.objects.filter(user=self.request.user).select_related('hospital').first()
			if not hospital_admin or obj.hospital_id != hospital_admin.hospital_id:
				raise PermissionDenied
		return obj

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		doctor = self.object
		context.update({
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

	def delete(self, request, *args, **kwargs):
		doctor = self.get_object()
		doctor_name = doctor.user.get_full_name() or doctor.user.username
		
		# Check if doctor has incomplete appointments
		incomplete_appointment_statuses = ['SCHEDULED', 'FOLLOW_UP', 'RESCHEDULED']
		incomplete_appointments = PatientAppointment.objects.filter(
			doctor=doctor,
			status__in=incomplete_appointment_statuses
		).exists()
		
		if incomplete_appointments:
			messages.error(
				request, 
				f'Cannot delete Dr. {doctor_name} because they have incomplete appointments. '
				'Please complete or cancel all appointments first.'
			)
			return redirect('doctors:doctor_detail', pk=doctor.pk)
		
		user = doctor.user  # Keep reference to user before deleting doctor

		try:
			with transaction.atomic():
				doctor.delete()  # Delete doctor profile first
				user.delete()    # Then delete the user
			messages.success(request, f'Doctor {doctor_name} deleted successfully.')
		except IntegrityError as exc:
			messages.error(request, f'Could not delete doctor: {exc}')
			return redirect('doctors:doctor_detail', pk=doctor.pk)

		return redirect(self.success_url)

class DoctorUpdateView(SuperAdminAndAdminOnlyMixin, UpdateView):
	"""Update doctor user and profile details"""
	model = Doctor
	template_name = 'doctors/doctor_edit.html'
	form_class = DoctorProfileForm
	success_url = reverse_lazy('doctors:doctor_list')

	def get_queryset(self):
		return Doctor.objects.select_related('user', 'hospital', 'department')

	def get_object(self, queryset=None):
		obj = super().get_object(queryset)
		if self.request.user.is_admin:
			hospital_admin = HospitalAdmin.objects.filter(user=self.request.user).select_related('hospital').first()
			if not hospital_admin or obj.hospital_id != hospital_admin.hospital_id:
				raise PermissionDenied
		return obj

	def get_hospitals(self):
		if self.request.user.is_super_admin:
			return Hospital.objects.all().order_by('name')

		hospital_admin = HospitalAdmin.objects.filter(user=self.request.user).select_related('hospital').first()
		if hospital_admin:
			return Hospital.objects.filter(id=hospital_admin.hospital_id)

		return Hospital.objects.none()

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		doctor = self.object
		user_form = kwargs.get('user_form') or DoctorUserUpdateForm(instance=doctor.user)
		doctor_form = kwargs.get('doctor_form') or context.get('form')

		context['doctor'] = doctor
		context['user_form'] = user_form
		context['doctor_form'] = doctor_form
		context['hospitals'] = self.get_hospitals()
		context['hospital_id'] = doctor.hospital_id
		return context

	def post(self, request, *args, **kwargs):
		doctor = self.get_object()
		self.object = doctor  # Set self.object for get_context_data()

		if request.user.is_super_admin:
			hospital_id = request.POST.get('hospital')
			if not hospital_id:
				messages.error(request, 'Please select a hospital.')
				return self.render_to_response(
					self.get_context_data(
						user_form=DoctorUserUpdateForm(instance=doctor.user),
						doctor_form=DoctorProfileForm(instance=doctor),
					)
				)
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

				messages.success(request, 'Doctor profile updated successfully.')
				return redirect(self.success_url)
			except IntegrityError as exc:
				messages.error(request, f'Error updating doctor: {exc}')
				return self.render_to_response(
					self.get_context_data(
						user_form=user_form,
						doctor_form=doctor_form,
					)
				)

		messages.error(request, 'Please correct the errors below.')
		return self.render_to_response(
			self.get_context_data(
				user_form=user_form,
				doctor_form=doctor_form,
			)
		)


