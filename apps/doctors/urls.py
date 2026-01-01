from django.urls import path

from .views import (
    DoctorCreateView,
    DoctorDeleteView,
    DoctorDetailView,
    DoctorListView,
    DoctorProfileEditView,
    DoctorScheduleCreateView,
    DoctorScheduleDetailView,
    DoctorScheduleListView,
    DoctorScheduleUpdateView,
    DoctorUpdateView,
)

app_name = 'doctors'

urlpatterns = [
    path('', DoctorListView.as_view(), name='doctor_list'),
    path('create/', DoctorCreateView.as_view(), name='doctor_create'),
    path('<int:pk>/', DoctorDetailView.as_view(), name='doctor_detail'),
    path('<int:pk>/edit/', DoctorUpdateView.as_view(), name='doctor_edit'),
    path('<int:pk>/delete/', DoctorDeleteView.as_view(), name='doctor_delete'),
    path('schedule/', DoctorScheduleListView.as_view(), name='doctor_schedule_list'),
    path('schedule/create/', DoctorScheduleCreateView.as_view(), name='doctor_schedule_create'),
    path('schedule/<int:pk>/', DoctorScheduleDetailView.as_view(), name='doctor_schedule_detail'),
    path('schedule/<int:pk>/edit/', DoctorScheduleUpdateView.as_view(), name='doctor_schedule_edit'),
    path('profile/', DoctorProfileEditView.as_view(), name='doctor_profile'),
]
