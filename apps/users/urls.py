from django.urls import path
from .views import (
    UserRegisterView, UserLoginView, UserLogoutView, 
    AdministerLoginView,AdministerLogoutView,
    AdminUserListView, AdminUserDetailView, 
    AdminUserUpdateView, AdminUserDeleteView,
    HospitalAdminUserListView, HospitalAdminUserCreateView, HospitalAdminUserDetailView,
    HospitalAdminUserUpdateView, HospitalAdminUserDeleteView
)

app_name = 'users'

urlpatterns = [
    # Authentication URLs
    path('register/', UserRegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('administer/login/', AdministerLoginView.as_view(), name='administer_login'),
    path('administer/logout/', AdministerLogoutView.as_view(), name='administer_logout'),
    
    # Super Admin User Management URLs
    path('admin/users/', AdminUserListView.as_view(), name='admin_user_list'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin_user_detail'),
    path('admin/users/<int:pk>/edit/', AdminUserUpdateView.as_view(), name='admin_user_update'),
    path('admin/users/<int:pk>/delete/', AdminUserDeleteView.as_view(), name='admin_user_delete'),
    
    # Hospital Admin User Management URLs (for their hospital only)
    path('hospital/users/', HospitalAdminUserListView.as_view(), name='hospital_user_list'),
    path('hospital/users/create/', HospitalAdminUserCreateView.as_view(), name='hospital_user_create'),
    path('hospital/users/<int:pk>/', HospitalAdminUserDetailView.as_view(), name='hospital_user_detail'),
    path('hospital/users/<int:pk>/edit/', HospitalAdminUserUpdateView.as_view(), name='hospital_user_update'),
    path('hospital/users/<int:pk>/delete/', HospitalAdminUserDeleteView.as_view(), name='hospital_user_delete'),
]
