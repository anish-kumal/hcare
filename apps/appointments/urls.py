from django.urls import path
from .views import (

    DoctorDetailView,
    AppointmentCreateView,
    BookingConfirmationView,
    AppointmentDetailView,
    AppointmentEditView,
    AppointmentDoctorListView,
    AppointmentDoctorScheduleView,
    PatientPrescriptionDetailView,
    AdminAppointmentCreateView,
    AdminAppointmentListView,
    AdminAppointmentDetailView,
    AdminAppointmentUpdateView,
    AdminAppointmentRescheduleView,
    AdminPrescriptionCreateView,
    AdminPrescriptionListView,
    AdminPrescriptionDetailView,
    AdminPrescriptionUpdateView,
    AdminPrescriptionDeleteView,
)

from apps.ai.views import  DoctorListView

app_name = 'appointments'

urlpatterns = [
    path('doctors/', DoctorListView.as_view(), name='doctor_list'),
    path('doctors/<int:pk>/', DoctorDetailView.as_view(), name='doctor_detail'),
    path('doctors/<int:doctor_id>/book/', AppointmentCreateView.as_view(), name='book_appointment'),
    path('confirmation/', BookingConfirmationView.as_view(), name='booking_confirmation'),
    path('appointment/<int:pk>/', AppointmentDetailView.as_view(), name='appointment_detail'),
    path('appointment/<int:pk>/edit/', AppointmentEditView.as_view(), name='appointment_edit'),
    path('prescriptions/<int:pk>/', PatientPrescriptionDetailView.as_view(), name='patient_prescription_detail'),
    path('manage-doctors/', AppointmentDoctorListView.as_view(), name='appointment_doctor_list'),
    path('manage-doctors/<int:pk>/schedule/', AppointmentDoctorScheduleView.as_view(), name='appointment_doctor_schedule'),
    path('manage-doctors/<int:doctor_id>/book/', AdminAppointmentCreateView.as_view(), name='appointment_admin_book'),
    path('manage/', AdminAppointmentListView.as_view(), name='appointment_list'),
    path('manage/<int:pk>/', AdminAppointmentDetailView.as_view(), name='appointment_manage_detail'),
    path('manage/<int:pk>/edit/', AdminAppointmentUpdateView.as_view(), name='appointment_manage_edit'),
    path('manage/<int:pk>/reschedule/', AdminAppointmentRescheduleView.as_view(), name='appointment_manage_reschedule'),
    path('manage/<int:appointment_id>/prescription/create/', AdminPrescriptionCreateView.as_view(), name='appointment_prescription_create'),
    path('manage/prescriptions/', AdminPrescriptionListView.as_view(), name='appointment_prescription_list'),
    path('manage/prescriptions/<int:pk>/', AdminPrescriptionDetailView.as_view(), name='appointment_prescription_detail'),
    path('manage/prescriptions/<int:pk>/edit/', AdminPrescriptionUpdateView.as_view(), name='appointment_prescription_edit'),
    path('manage/prescriptions/<int:pk>/delete/', AdminPrescriptionDeleteView.as_view(), name='appointment_prescription_delete'),
]
