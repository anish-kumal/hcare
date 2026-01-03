from django.urls import path
from .views import (
    PatientCreateView,
    PatientProfileView,
    PatientListView,
    PatientDetailView,
    PatientUpdateView,
    PatientDeleteView,
)

app_name = 'patients'

urlpatterns = [
    path('', PatientListView.as_view(), name='patient_list'),
    path('create/', PatientCreateView.as_view(), name='patient_create'),
    path('profile/', PatientProfileView.as_view(), name='patient_profile'),
    path('<int:pk>/', PatientDetailView.as_view(), name='patient_detail'),
    path('<int:pk>/edit/', PatientUpdateView.as_view(), name='patient_update'),
    path('<int:pk>/delete/', PatientDeleteView.as_view(), name='patient_delete'),
]
