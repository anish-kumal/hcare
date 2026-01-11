from django.urls import path
from .views import PatientProfileView

app_name = 'patients'

urlpatterns = [
    path('profile/', PatientProfileView.as_view(), name='patient_profile'),
]
