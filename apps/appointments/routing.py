from django.urls import re_path

from .consumers import DoctorSlotsConsumer


websocket_urlpatterns = [
    re_path(r'^ws/appointments/doctors/(?P<doctor_id>\d+)/slots/$', DoctorSlotsConsumer.as_asgi()),
]
