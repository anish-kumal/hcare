from django.contrib import messages
from datetime import timedelta
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from apps.appointments.forms import MedicineFormSet, PrescriptionForm
from apps.appointments.models import Prescription
from apps.appointments.views import DoctorAccessMixin, PatientAccessMixin
from apps.base.mixin import AdminHospitalScopedQuerysetMixin, AdminPharmacistOnlyMixin, SuperAdminAndAdminOnlyMixin
from apps.patients.models import PatientAppointment


class PatientPrescriptionDetailView(PatientAccessMixin, DetailView):
	"""Show prescription detail for the logged-in patient only."""

	model = Prescription
	template_name = 'patients/prescription_detail.html'
	context_object_name = 'prescription'

	def get_queryset(self):
		return Prescription.objects.filter(
			appointment__patient__user=self.request.user,
		).select_related(
			'appointment__patient__user',
			'appointment__doctor__user',
			'appointment__doctor__hospital',
		).prefetch_related('medicines')


class DoctorPrescriptionCreateView(DoctorAccessMixin, CreateView):
	"""Create prescription for a doctor's own appointment."""

	model = Prescription
	form_class = PrescriptionForm
	template_name = 'appointments/prescription_form.html'

	def get_appointment(self):
		return get_object_or_404(
			PatientAppointment.objects.select_related('patient__user', 'doctor__user', 'hospital'),
			pk=self.kwargs.get('appointment_id'),
			doctor__user=self.request.user,
		)

	def dispatch(self, request, *args, **kwargs):
		appointment = self.get_appointment()
		if hasattr(appointment, 'prescription_record'):
			messages.warning(request, 'Prescription already exists for this appointment.')
			return redirect('appointments:doctor_appointment_detail', pk=appointment.pk)
		return super().dispatch(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['appointment'] = self.get_appointment()
		context['is_doctor_portal'] = True
		if self.request.POST:
			context['medicine_formset'] = MedicineFormSet(self.request.POST)
		else:
			context['medicine_formset'] = MedicineFormSet()
		return context

	def form_valid(self, form):
		appointment = self.get_appointment()
		context = self.get_context_data(form=form)
		medicine_formset = context['medicine_formset']

		if not medicine_formset.is_valid():
			messages.error(self.request, 'Please correct medicine form errors below.')
			return self.render_to_response(context)

		with transaction.atomic():
			form.instance.appointment = appointment
			form.instance.created_by = self.request.user
			self.object = form.save()

			medicine_formset.instance = self.object
			medicines = medicine_formset.save(commit=False)
			for medicine in medicines:
				medicine.created_by = self.request.user
				medicine.save()
			for deleted_medicine in medicine_formset.deleted_objects:
				deleted_medicine.delete()

		messages.success(self.request, 'Prescription saved successfully.')
		return redirect('appointments:doctor_appointment_detail', pk=appointment.pk)


class DoctorPrescriptionDetailView(DoctorAccessMixin, DetailView):
	"""View prescription details for current doctor's appointments."""

	model = Prescription
	template_name = 'appointments/prescription_detail.html'
	context_object_name = 'prescription'

	def get_queryset(self):
		return Prescription.objects.filter(
			appointment__doctor__user=self.request.user,
		).select_related(
			'appointment__patient__user',
			'appointment__doctor__user',
			'appointment__hospital',
			'created_by',
		).prefetch_related('medicines')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['is_doctor_portal'] = True
		context['can_edit_prescription'] = self.object.created_by_id == self.request.user.id
		return context


class DoctorPrescriptionUpdateView(DoctorAccessMixin, UpdateView):
	"""Allow editing prescription only if created by the current doctor."""

	model = Prescription
	form_class = PrescriptionForm
	template_name = 'appointments/prescription_form.html'
	context_object_name = 'prescription'

	def get_queryset(self):
		return Prescription.objects.filter(
			appointment__doctor__user=self.request.user,
			created_by=self.request.user,
		).select_related(
			'appointment__patient__user',
			'appointment__doctor__user',
			'appointment__hospital',
			'created_by',
		).prefetch_related('medicines')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['appointment'] = self.object.appointment
		context['is_edit'] = True
		context['is_doctor_portal'] = True
		if self.request.POST:
			context['medicine_formset'] = MedicineFormSet(self.request.POST, instance=self.object)
		else:
			context['medicine_formset'] = MedicineFormSet(instance=self.object)
		return context

	def form_valid(self, form):
		context = self.get_context_data(form=form)
		medicine_formset = context['medicine_formset']

		if not medicine_formset.is_valid():
			messages.error(self.request, 'Please correct medicine form errors below.')
			return self.render_to_response(context)

		with transaction.atomic():
			self.object = form.save()

			medicine_formset.instance = self.object
			medicines = medicine_formset.save(commit=False)
			for medicine in medicines:
				if not medicine.created_by:
					medicine.created_by = self.request.user
				medicine.save()
			for deleted_medicine in medicine_formset.deleted_objects:
				deleted_medicine.delete()

		messages.success(self.request, 'Prescription updated successfully.')
		return redirect('prescription:doctor_prescription_detail', pk=self.object.pk)

	def form_invalid(self, form):
		messages.error(self.request, 'Please correct the errors below.')
		return self.render_to_response(self.get_context_data(form=form))


class AdminPrescriptionCreateView(AdminHospitalScopedQuerysetMixin, SuperAdminAndAdminOnlyMixin, CreateView):
	"""Create prescription and medicine rows for an appointment."""

	model = Prescription
	form_class = PrescriptionForm
	template_name = 'appointments/prescription_form.html'

	def get_appointment(self):
		queryset = PatientAppointment.objects.select_related('patient__user', 'doctor__user', 'hospital')
		queryset = self.scope_queryset_for_admin(queryset, hospital_field='hospital_id')
		return get_object_or_404(queryset, pk=self.kwargs.get('appointment_id'))

	def dispatch(self, request, *args, **kwargs):
		appointment = self.get_appointment()
		if hasattr(appointment, 'prescription_record'):
			messages.warning(request, 'Prescription already exists for this appointment.')
			return redirect('appointments:appointment_manage_detail', pk=appointment.pk)
		return super().dispatch(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['appointment'] = self.get_appointment()
		if self.request.POST:
			context['medicine_formset'] = MedicineFormSet(self.request.POST)
		else:
			context['medicine_formset'] = MedicineFormSet()
		return context

	def form_valid(self, form):
		appointment = self.get_appointment()
		context = self.get_context_data(form=form)
		medicine_formset = context['medicine_formset']

		if not medicine_formset.is_valid():
			messages.error(self.request, 'Please correct medicine form errors below.')
			return self.render_to_response(context)

		with transaction.atomic():
			form.instance.appointment = appointment
			form.instance.created_by = self.request.user
			self.object = form.save()

			medicine_formset.instance = self.object
			medicines = medicine_formset.save(commit=False)
			for medicine in medicines:
				medicine.created_by = self.request.user
				medicine.save()
			for deleted_medicine in medicine_formset.deleted_objects:
				deleted_medicine.delete()

		messages.success(self.request, 'Prescription saved successfully.')
		return redirect('appointments:appointment_manage_detail', pk=appointment.pk)

	def form_invalid(self, form):
		messages.error(self.request, 'Please correct the errors below.')
		return self.render_to_response(self.get_context_data(form=form))


class AdminPrescriptionListView(AdminHospitalScopedQuerysetMixin, AdminPharmacistOnlyMixin, ListView):
	"""List prescriptions for admin/super-admin."""

	model = Prescription
	template_name = 'appointments/prescription_list.html'
	context_object_name = 'prescriptions'
	paginate_by = 10

	def get_queryset(self):
		queryset = Prescription.objects.filter(
			appointment__hospital__is_active=True,
		).select_related(
			'appointment__patient__user',
			'appointment__doctor__user',
			'appointment__hospital',
			'created_by',
		).prefetch_related('medicines').order_by('-created')
		queryset = self.scope_queryset_for_admin(queryset, hospital_field='appointment__hospital_id')

		search = self.request.GET.get('search', '').strip()
		if search:
			queryset = queryset.filter(
				Q(appointment__patient__user__first_name__icontains=search)
				| Q(appointment__patient__user__last_name__icontains=search)
				| Q(appointment__patient__booking_uuid__icontains=search)
				| Q(appointment__doctor__user__first_name__icontains=search)
				| Q(appointment__doctor__user__last_name__icontains=search)
				| Q(diagnosis__icontains=search)
			)

		return queryset

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['search_query'] = self.request.GET.get('search', '').strip()
		prescriptions = self.scope_queryset_for_admin(
			Prescription.objects.filter(appointment__hospital__is_active=True),
			hospital_field='appointment__hospital_id',
		)
		today = timezone.localdate()
		week_start = today - timedelta(days=today.weekday())
		week_end = week_start + timedelta(days=6)
		context['analytics_cards'] = [
			{'label': 'Total Prescriptions', 'value': prescriptions.count(), 'value_class': 'text-gray-900', 'icon': 'prescriptions'},
			{'label': 'Created Today', 'value': prescriptions.filter(created__date=today).count(), 'value_class': 'text-blue-700', 'icon': 'today'},
			{
				'label': 'Created This Week',
				'value': prescriptions.filter(created__date__range=(week_start, week_end)).count(),
				'value_class': 'text-emerald-700',
				'icon': 'date_range',
			},
		]
		return context


class AdminPrescriptionDetailView(AdminHospitalScopedQuerysetMixin, AdminPharmacistOnlyMixin, DetailView):
	"""Show prescription detail for admin/super-admin."""

	model = Prescription
	template_name = 'appointments/prescription_detail.html'
	context_object_name = 'prescription'

	def get_queryset(self):
		queryset = Prescription.objects.select_related(
			'appointment__patient__user',
			'appointment__doctor__user',
			'appointment__hospital',
			'created_by',
		).prefetch_related('medicines')
		return self.scope_queryset_for_admin(queryset, hospital_field='appointment__hospital_id')


class AdminPrescriptionUpdateView(AdminHospitalScopedQuerysetMixin, SuperAdminAndAdminOnlyMixin, UpdateView):
	"""Update prescription and medicine rows for admin/super-admin."""

	model = Prescription
	form_class = PrescriptionForm
	template_name = 'appointments/prescription_form.html'
	context_object_name = 'prescription'

	def get_queryset(self):
		queryset = Prescription.objects.select_related(
			'appointment__patient__user',
			'appointment__doctor__user',
			'appointment__hospital',
			'created_by',
		).prefetch_related('medicines')
		return self.scope_queryset_for_admin(queryset, hospital_field='appointment__hospital_id')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['appointment'] = self.object.appointment
		context['is_edit'] = True
		if self.request.POST:
			context['medicine_formset'] = MedicineFormSet(self.request.POST, instance=self.object)
		else:
			context['medicine_formset'] = MedicineFormSet(instance=self.object)
		return context

	def form_valid(self, form):
		context = self.get_context_data(form=form)
		medicine_formset = context['medicine_formset']

		if not medicine_formset.is_valid():
			messages.error(self.request, 'Please correct medicine form errors below.')
			return self.render_to_response(context)

		with transaction.atomic():
			self.object = form.save()

			medicine_formset.instance = self.object
			medicines = medicine_formset.save(commit=False)
			for medicine in medicines:
				if not medicine.created_by:
					medicine.created_by = self.request.user
				medicine.save()
			for deleted_medicine in medicine_formset.deleted_objects:
				deleted_medicine.delete()

		messages.success(self.request, 'Prescription updated successfully.')
		return redirect('prescription:appointment_prescription_detail', pk=self.object.pk)

	def form_invalid(self, form):
		messages.error(self.request, 'Please correct the errors below.')
		return self.render_to_response(self.get_context_data(form=form))


class AdminPrescriptionDeleteView(AdminHospitalScopedQuerysetMixin, SuperAdminAndAdminOnlyMixin, DeleteView):
	"""Delete prescription for admin/super-admin."""

	model = Prescription
	template_name = 'partials/delete.html'

	def get_queryset(self):
		queryset = Prescription.objects.select_related('appointment__patient__user', 'appointment__doctor__user')
		return self.scope_queryset_for_admin(queryset, hospital_field='appointment__hospital_id')

	def get_success_url(self):
		return reverse_lazy('prescription:appointment_prescription_list')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		patient_name = '-'
		if self.object.appointment and self.object.appointment.patient and self.object.appointment.patient.user:
			patient_name = self.object.appointment.patient.user.get_full_name() or self.object.appointment.patient.user.username

		context.update({
			'delete_page_title': 'Delete Prescription - Health Care',
			'delete_confirm_title': f'Delete Prescription #{self.object.pk}?',
			'delete_confirm_message': (
				f'Are you sure you want to delete this prescription for {patient_name}?'
			),
			'delete_warning_text': (
				'Deleting this prescription will permanently remove all related medicine rows.'
			),
			'delete_button_label': 'Delete Prescription',
			'cancel_url': reverse_lazy('prescription:appointment_prescription_detail', kwargs={'pk': self.object.pk}),
		})
		return context

	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, 'Prescription deleted successfully.')
		return response
