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
    AboutView,
    TermsView,
    PrivacyPolicyView,
    ServicesView,
    ContactView,
    AdministrView,
    SuperAdminDashboardView, 
    AdminDashboardView,
    DoctorDashboardView,
    PatientDashboardView,
    LabAssistantDashboardView,
    PharmacistDashboardView,
    StaffDashboardView,
    Custom404View,
    Custom500View,
    Custom403View,
    Custom400View,
    AdministerAboutView,
    HowItWorksView,
    AdministerContactView,
    AdministerPricingView,
    ContactListView,
    ContactDetailsView,
)


urlpatterns = [
    # Public routes
    path('', IndexView.as_view(), name='index'),
    path('about/', AboutView.as_view(), name='about'),
    path('services/', ServicesView.as_view(), name='services'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('terms/', TermsView.as_view(), name='terms'),
    path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy_policy'),
    
    # App-specific routes
    path('auth/', include('apps.users.urls')),
    path('social-auth/', include('allauth.urls')),
    path('otp/', include('apps.otp.urls')),
    path('hospitals/', include('apps.hospitals.urls')),
    path('doctors/', include('apps.doctors.urls')),
    path('patients/', include('apps.patients.urls')),
    path('appointments/', include('apps.appointments.urls')),
    path('payments/', include('apps.payments.urls')),
    path('medical-reports/', include('apps.medical_report.urls')),
    path('logs/', include('apps.logs.urls')),
    path('contacts/', ContactListView.as_view(), name='contact_list'),
    path('contacts/<int:pk>/', ContactDetailsView.as_view(), name='contact_detail'),
    path('prescriptions/', include('apps.prescription.urls', 'prescription')),

    # Dashboard routes based on role
    path('dashboard/super-admin/', SuperAdminDashboardView.as_view(), name='super_admin_dashboard'),
    path('dashboard/admin/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('dashboard/doctor/', DoctorDashboardView.as_view(), name='doctor_dashboard'),
    path('dashboard/patient/', PatientDashboardView.as_view(), name='patient_dashboard'),
    path('dashboard/lab-assistant/', LabAssistantDashboardView.as_view(), name='lab_assistant_dashboard'),
    path('dashboard/pharmacist/', PharmacistDashboardView.as_view(), name='pharmacist_dashboard'),
    path('dashboard/staff/', StaffDashboardView.as_view(), name='staff_dashboard'),

    # Administer onboarding pages
    path('admin/', admin.site.urls),
    path('administer/', AdministrView.as_view(), name='administer'),
    path('about_administer/', AdministerAboutView.as_view(), name='about_administer'),
    path('how-it-works/', HowItWorksView.as_view(), name='how_it_works'),
    path('contact_administer/', AdministerContactView.as_view(), name='contact_administer'),
    path('pricing/', AdministerPricingView.as_view(), name='pricing_administer'),

]

if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]

if settings.SERVE_MEDIA:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = Custom404View.as_view()
handler500 = Custom500View.as_view()
handler403 = Custom403View.as_view()
handler400 = Custom400View.as_view()