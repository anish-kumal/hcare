from django.urls import path

from .views import (
    DoctorProfileEditView,
    DoctorScheduleCreateView,
    DoctorScheduleDetailView,
    DoctorScheduleListView,
    DoctorScheduleUpdateView,
)

app_name = 'doctors'

urlpatterns = [
    path('schedule/', DoctorScheduleListView.as_view(), name='doctor_schedule_list'),
    path('schedule/create/', DoctorScheduleCreateView.as_view(), name='doctor_schedule_create'),
    path('schedule/<int:pk>/', DoctorScheduleDetailView.as_view(), name='doctor_schedule_detail'),
    path('schedule/<int:pk>/edit/', DoctorScheduleUpdateView.as_view(), name='doctor_schedule_edit'),
    path('profile/', DoctorProfileEditView.as_view(), name='doctor_profile'),
]
