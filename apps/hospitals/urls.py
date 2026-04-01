from django.urls import path
from .views import (
    HospitalListView,
    HospitalDetailView,
    HospitalCreateView,
    HospitalUpdateView,
    HospitalDeleteView,
    HospitalAdminListView,
    HospitalAdminCreateView,
    HospitalAdminDetailView,
    HospitalAdminUpdateView,
    HospitalAdminDeleteView,
    AdminOwnHospitalDetailView,
    AdminOwnHospitalUpdateView,
    HospitalDepartmentListView,
    HospitalDepartmentCreateView,
    HospitalDepartmentUpdateView,
    HospitalDepartmentDeleteView,
    HospitalRegistartionView,
    KhaltiSetupView,
)

app_name = 'hospitals'

urlpatterns = [
    # Hospital CRUD URLs
    path('', HospitalListView.as_view(), name='hospital_list'),
    path('create/', HospitalCreateView.as_view(), name='hospital_create'),
    path('<int:pk>/', HospitalDetailView.as_view(), name='hospital_detail'),
    path('<int:pk>/edit/', HospitalUpdateView.as_view(), name='hospital_update'),
    path('<int:pk>/delete/', HospitalDeleteView.as_view(), name='hospital_delete'),
    
    # Hospital Admin CRUD URLs
    path('<int:hospital_id>/admins/', HospitalAdminListView.as_view(), name='hospital_admin_list'),
    path('<int:hospital_id>/admins/add/', HospitalAdminCreateView.as_view(), name='hospital_admin_create'),
    path('admins/<int:pk>/', HospitalAdminDetailView.as_view(), name='hospital_admin_detail'),
    path('admins/<int:pk>/edit/', HospitalAdminUpdateView.as_view(), name='hospital_admin_update'),
    path('admins/<int:pk>/delete/', HospitalAdminDeleteView.as_view(), name='hospital_admin_delete'),
    
    # Hospital Admin Own Hospital URLs
    path('admin/hospital/', AdminOwnHospitalDetailView.as_view(), name='admin_hospital_detail'),
    path('admin/hospital/edit/', AdminOwnHospitalUpdateView.as_view(), name='admin_hospital_update'),
    path('admin/hospital/khalti-setup/', KhaltiSetupView.as_view(), name='khalti_setup'),
    path('admin/hospital/departments/', HospitalDepartmentListView.as_view(), name='hospital_department_list'),
    path('admin/hospital/departments/add/', HospitalDepartmentCreateView.as_view(), name='hospital_department_create'),
    path('admin/hospital/departments/<int:pk>/edit/', HospitalDepartmentUpdateView.as_view(), name='hospital_department_update'),
    path('admin/hospital/departments/<int:pk>/delete/', HospitalDepartmentDeleteView.as_view(), name='hospital_department_delete'),
    # Public hospital registration
    path('register/', HospitalRegistartionView.as_view(), name='hospital_registration'),
    # 
    path('admin/hospital/khalti-setup/', KhaltiSetupView.as_view(), name='khalti_setup'),
]
