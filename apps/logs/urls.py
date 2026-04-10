from django.urls import path
from . import views

app_name = 'logs'

urlpatterns = [
    # Audit log views
    path('audit/', views.AuditLogListView.as_view(), name='auditlog_list'),
    path('audit/<int:pk>/', views.AuditLogDetailView.as_view(), name='auditlog_detail'),
    
]
