from django.urls import path
from .views import (
    PatientCreateView,
    PatientSelfProfileCreateView,
    PatientProfileView,
    PatientProfileEditView,
    PatientAccountEditView,
    PatientPasswordChangeView,
    PatientListView,
    PatientDetailView,
    PatientUpdateView,
    PatientDeleteView,
)

app_name = 'patients'

urlpatterns = [
    path('', PatientListView.as_view(), name='patient_list'),
    path('create/', PatientCreateView.as_view(), name='patient_create'),
    path('profile/create/', PatientSelfProfileCreateView.as_view(), name='patient_profile_create'),
    path('profile/', PatientProfileView.as_view(), name='patient_profile'),
    path('profile/edit/', PatientProfileEditView.as_view(), name='patient_profile_edit'),
    path('profile/edit/account/', PatientAccountEditView.as_view(), name='patient_account_edit'),
    path('profile/edit/password/', PatientPasswordChangeView.as_view(), name='patient_password_change'),
    path('<int:pk>/', PatientDetailView.as_view(), name='patient_detail'),
    path('<int:pk>/edit/', PatientUpdateView.as_view(), name='patient_update'),
    path('<int:pk>/delete/', PatientDeleteView.as_view(), name='patient_delete'),
]
