from django.urls import path
from . import views

app_name = 'medical_report'

urlpatterns = [
    
    # Admin Medical Report URLs
    path('admin/list/', views.AdminMedicalReportListView.as_view(), name='admin_medical_report_list'),
    path('admin/<int:pk>/', views.AdminMedicalReportDetailView.as_view(), name='admin_medical_report_detail'),
    path('admin/<int:pk>/edit/', views.AdminMedicalReportUpdateView.as_view(), name='admin_medical_report_update'),
    path('admin/<int:pk>/delete/', views.AdminMedicalReportDeleteView.as_view(), name='admin_medical_report_delete'),
]
