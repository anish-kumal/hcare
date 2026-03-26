from django.urls import path
from .views import (
    UserRegisterView, UserLoginView, UserLogoutView, 
    AdministerLoginView, AdministerLogoutView,
    UserListView, UserDetailView, 
    UserUpdateView, UserDeleteView,UserCreateView,PasswordChangeView

)

app_name = 'users'

urlpatterns = [
    # Authentication URLs
    path('register/', UserRegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('administer/login/', AdministerLoginView.as_view(), name='administer_login'),
    path('administer/logout/', AdministerLogoutView.as_view(), name='administer_logout'),
    
    # Super  User Management URLs
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('users/create/', UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/edit/', UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', UserDeleteView.as_view(), name='user_delete'),

    path('password_change/', PasswordChangeView.as_view(), name='password_change'),
    

]
