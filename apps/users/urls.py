from django.urls import path
from .views import UserRegisterView, UserLoginView, UserLogoutView, PasswordResetView

app_name = 'users'

urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('password-reset/<int:user_id>/', PasswordResetView.as_view(), name='password_reset'),
]
