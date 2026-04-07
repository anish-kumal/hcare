from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from apps.patients.models import Patient, PatientAppointment
from .models import Prescription, Medicine


class HospitalPatientChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        full_name = obj.user.get_full_name() or obj.user.username
        return f"{full_name} | ID: {obj.id} | UUID: {obj.booking_uuid} | Gender: {obj.get_gender_display()}"


class AppointmentBookingForm(forms.ModelForm):
    """Form for patients to book appointments"""
    
    class Meta:
        model = PatientAppointment
        fields = ['appointment_date', 'appointment_time', 'reason', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True,
            }),
            'appointment_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control',
                'required': True,
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Please describe the reason for your visit',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any additional notes (optional)',
            }),
        }


class AppointmentEditForm(forms.ModelForm):
    """Form for patients to edit their appointments"""

    class Meta:
        model = PatientAppointment
        fields = ['appointment_date', 'appointment_time', 'status', 'reason', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700 cursor-not-allowed',
                'readonly': True,
                'required': True,
            }),
            'appointment_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700 cursor-not-allowed',
                'readonly': True,
                'required': True,
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
            }),
            'reason': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'rows': 3,
                'placeholder': 'Please describe the reason for your visit',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'rows': 3,
                'placeholder': 'Any additional notes (optional)',
            }),
        }


    def clean_status(self):
        new_status = self.cleaned_data.get('status')
        current_status = getattr(self.instance, 'status', None)

        restricted_transitions = {
            ('FOLLOW_UP', 'SCHEDULED'),
            ('FOLLOW_UP', 'RESCHEDULED'),
            ('SCHEDULED', 'FOLLOW_UP'),
            ('SCHEDULED', 'RESCHEDULED'),
            ('RESCHEDULED', 'FOLLOW_UP'),
            ('RESCHEDULED', 'SCHEDULED'),
        }

        if current_status and new_status and (current_status, new_status) in restricted_transitions:
            raise forms.ValidationError(
                f"Cannot change status from {current_status} to {new_status}. Please contact support for assistance."
            )

        return new_status

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.status in ['COMPLETED', 'CANCELLED']:
            for field_name in ['appointment_date', 'appointment_time', 'status', 'reason', 'notes']:
                self.fields[field_name].disabled = True


class AdminAppointmentBookingForm(forms.ModelForm):
    """Form for admin/staff to book appointment for hospital patients"""

    patient = HospitalPatientChoiceField(
        queryset=Patient.objects.none(),
        required=False,
        empty_label='Select patient from hospital',
    )
    booking_uuid = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter patient booking UUID',
        }),
        help_text='Use only when selecting by booking UUID.',
    )

    class Meta:
        model = PatientAppointment
        fields = ['patient', 'booking_uuid', 'appointment_date', 'appointment_time', 'reason', 'notes']
        widgets = {
            'appointment_date': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 cursor-not-allowed',
                'readonly': True,
                'required': True,
            }),
            'appointment_time': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 cursor-not-allowed',
                'readonly': True,
                'required': True,
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for appointment',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.hospital = kwargs.pop('hospital', None)
        super().__init__(*args, **kwargs)

        # Show ALL patients in dropdown (not restricted by hospital)
        all_patients = Patient.objects.select_related('user').order_by('user__first_name', 'user__last_name')
        self.fields['patient'].queryset = all_patients

        self.fields['patient'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
        })
        self.fields['booking_uuid'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
        })
        self.fields['reason'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
        })
        self.fields['notes'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
        })
        
        # appointment_date and appointment_time are read-only (set in widgets)

    def clean(self):
        cleaned_data = super().clean()
        selected_patient = cleaned_data.get('patient')
        booking_uuid = (cleaned_data.get('booking_uuid') or '').strip()

        if selected_patient and booking_uuid:
            raise forms.ValidationError('Choose either patient dropdown or booking UUID, not both.')

        if not selected_patient and not booking_uuid:
            raise forms.ValidationError('Select a patient or provide a booking UUID.')

        if booking_uuid:
            try:
                selected_patient = Patient.objects.select_related('user').get(booking_uuid=booking_uuid)
            except Patient.DoesNotExist:
                self.add_error('booking_uuid', 'No patient found for this booking UUID.')
                return cleaned_data

            cleaned_data['patient'] = selected_patient

        return cleaned_data


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['diagnosis', 'notes']
        widgets = {
            'diagnosis': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'rows': 4,
                'placeholder': 'Enter diagnosis and clinical findings',
                'required': True,
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'rows': 3,
                'placeholder': 'Additional notes (optional)',
            }),
        }


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ['name', 'dosage', 'frequency', 'duration', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Medicine name',
            }),
            'dosage': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'e.g. 500mg',
            }),
            'frequency': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'e.g. 2 times a day',
            }),
            'duration': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'e.g. 5 days',
            }),
            'notes': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'Medicine notes (optional)',
            }),
        }


class BaseMedicineFormSet(BaseInlineFormSet):
    """Validate medicine fields only when a medicine row is present in POST data."""

    required_medicine_fields = ('name', 'dosage', 'frequency', 'duration')

    def clean(self):
        super().clean()

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue

            if self.can_delete and self._should_delete_form(form):
                continue

            # For a posted medicine row, require core fields.
            has_any_value = any((form.cleaned_data.get(field) or '').strip() for field in self.required_medicine_fields)
            if not has_any_value:
                form.add_error('name', 'Please fill medicine details or remove this row.')
                continue

            for field in self.required_medicine_fields:
                if not (form.cleaned_data.get(field) or '').strip():
                    form.add_error(field, 'This field is required.')


MedicineFormSet = inlineformset_factory(
    Prescription,
    Medicine,
    form=MedicineForm,
    formset=BaseMedicineFormSet,
    extra=0,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
