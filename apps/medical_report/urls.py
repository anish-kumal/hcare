from django.urls import path
from . import views

app_name = 'medical_report'

urlpatterns = [
    path('doctor/list/', views.DoctorMedicalReportListView.as_view(), name='doctor_medical_report_list'),
    path('doctor/create/', views.DoctorMedicalReportCreateView.as_view(), name='doctor_medical_report_create'),
    path('doctor/<int:pk>/', views.DoctorMedicalReportDetailView.as_view(), name='doctor_medical_report_detail'),
    path('doctor/<int:pk>/edit/', views.DoctorMedicalReportUpdateView.as_view(), name='doctor_medical_report_update'),
    path('doctor/<int:pk>/download/', views.DoctorMedicalReportDownloadView.as_view(), name='doctor_medical_report_download'),
    path('doctor/<int:pk>/view/', views.DoctorMedicalReportViewFileView.as_view(), name='doctor_medical_report_view'),

    path('patient/<int:pk>/', views.PatientMedicalReportDetailView.as_view(), name='patient_medical_report_detail'),
    path('patient/<int:pk>/edit/', views.PatientMedicalReportUpdateView.as_view(), name='patient_medical_report_edit'),
    path('patient/<int:pk>/download/', views.PatientMedicalReportDownloadView.as_view(), name='patient_medical_report_download'),
    path('patient/<int:pk>/view/', views.PatientMedicalReportViewFileView.as_view(), name='patient_medical_report_view'),
    
    # Admin Medical Report URLs
    path('admin/list/', views.AdminMedicalReportListView.as_view(), name='admin_medical_report_list'),
    path('admin/<int:pk>/', views.AdminMedicalReportDetailView.as_view(), name='admin_medical_report_detail'),
    path('admin/<int:pk>/download/', views.AdminMedicalReportDownloadView.as_view(), name='admin_medical_report_download'),
    path('admin/<int:pk>/view/', views.AdminMedicalReportViewFileView.as_view(), name='admin_medical_report_view'),
    path('admin/<int:pk>/edit/', views.AdminMedicalReportUpdateView.as_view(), name='admin_medical_report_update'),
    path('admin/<int:pk>/delete/', views.AdminMedicalReportDeleteView.as_view(), name='admin_medical_report_delete'),
    path('admin/create/', views.AdminMedicalReportCreateView.as_view(), name='admin_medical_report_create'),
]
