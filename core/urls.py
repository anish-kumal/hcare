"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.base.views import (
    IndexView, 
    AdministrView,
    SuperAdminDashboardView, 
    AdminDashboardView,
    DoctorDashboardView,
    PatientDashboardView,
    LabAssistantDashboardView,
    Custom404View,
    Custom500View,
)


urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('administer/', AdministrView.as_view(), name='administer'),
    path('admin/', admin.site.urls),
    path('auth/', include('apps.users.urls')),
    path('otp/', include('apps.otp.urls')),
    path('hospitals/', include('apps.hospitals.urls')),
    path('doctors/', include('apps.doctors.urls')),
    path('patients/', include('apps.patients.urls')),
    path('appointments/', include('apps.appointments.urls')),
    # Dashboard routes based on role
    path('dashboard/super-admin/', SuperAdminDashboardView.as_view(), name='super_admin_dashboard'),
    path('dashboard/admin/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('dashboard/doctor/', DoctorDashboardView.as_view(), name='doctor_dashboard'),
    path('dashboard/patient/', PatientDashboardView.as_view(), name='patient_dashboard'),
    path('dashboard/lab-assistant/', LabAssistantDashboardView.as_view(), name='lab_assistant_dashboard'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


handler404 = Custom404View.as_view()
handler500 = Custom500View.as_view()