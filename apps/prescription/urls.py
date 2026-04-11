from django.urls import path

from .views import (
	AdminPrescriptionCreateView,
	AdminPrescriptionDeleteView,
	AdminPrescriptionDetailView,
	AdminPrescriptionListView,
	AdminPrescriptionUpdateView,
	DoctorPrescriptionCreateView,
	DoctorPrescriptionDetailView,
	DoctorPrescriptionUpdateView,
	PatientPrescriptionDetailView,
)


app_name = 'prescription'


urlpatterns = [
	path('<int:pk>/', PatientPrescriptionDetailView.as_view(), name='patient_prescription_detail'),
	path('doctor/<int:appointment_id>/create/', DoctorPrescriptionCreateView.as_view(), name='doctor_prescription_create'),
	path('doctor/<int:pk>/', DoctorPrescriptionDetailView.as_view(), name='doctor_prescription_detail'),
	path('doctor/<int:pk>/edit/', DoctorPrescriptionUpdateView.as_view(), name='doctor_prescription_edit'),
	path('manage/<int:appointment_id>/create/', AdminPrescriptionCreateView.as_view(), name='appointment_prescription_create'),
	path('manage/', AdminPrescriptionListView.as_view(), name='appointment_prescription_list'),
	path('manage/<int:pk>/', AdminPrescriptionDetailView.as_view(), name='appointment_prescription_detail'),
	path('manage/<int:pk>/edit/', AdminPrescriptionUpdateView.as_view(), name='appointment_prescription_edit'),
	path('manage/<int:pk>/delete/', AdminPrescriptionDeleteView.as_view(), name='appointment_prescription_delete'),
]
