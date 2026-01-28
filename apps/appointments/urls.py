from django.urls import path
from .views import (
    DoctorListView,
    DoctorDetailView,
    AppointmentCreateView,
    BookingConfirmationView,
    AppointmentDetailView,
    AppointmentDoctorListView,
    AppointmentDoctorScheduleView,
    AdminAppointmentCreateView,
    AdminAppointmentListView,
    AdminAppointmentDetailView,
    AdminAppointmentUpdateView,
)

app_name = 'appointments'

urlpatterns = [
    path('doctors/', DoctorListView.as_view(), name='doctor_list'),
    path('doctors/<int:pk>/', DoctorDetailView.as_view(), name='doctor_detail'),
    path('doctors/<int:doctor_id>/book/', AppointmentCreateView.as_view(), name='book_appointment'),
    path('confirmation/', BookingConfirmationView.as_view(), name='booking_confirmation'),
    path('appointment/<int:pk>/', AppointmentDetailView.as_view(), name='appointment_detail'),
    path('manage-doctors/', AppointmentDoctorListView.as_view(), name='appointment_doctor_list'),
    path('manage-doctors/<int:pk>/schedule/', AppointmentDoctorScheduleView.as_view(), name='appointment_doctor_schedule'),
    path('manage-doctors/<int:doctor_id>/book/', AdminAppointmentCreateView.as_view(), name='appointment_admin_book'),
    path('manage/', AdminAppointmentListView.as_view(), name='appointment_list'),
    path('manage/<int:pk>/', AdminAppointmentDetailView.as_view(), name='appointment_manage_detail'),
    path('manage/<int:pk>/edit/', AdminAppointmentUpdateView.as_view(), name='appointment_manage_edit'),
]
