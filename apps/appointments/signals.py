from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.doctors.models import DoctorSchedule
from apps.patients.models import PatientAppointment


def _notify_doctor_slot_update(doctor_id):
    if not doctor_id:
        return

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f'doctor_slots_{doctor_id}',
        {
            'type': 'slots_updated',
            'doctor_id': doctor_id,
        },
    )


@receiver(post_save, sender=PatientAppointment)
def patient_appointment_saved(sender, instance, **kwargs):
    _notify_doctor_slot_update(getattr(instance, 'doctor_id', None))


@receiver(post_delete, sender=PatientAppointment)
def patient_appointment_deleted(sender, instance, **kwargs):
    _notify_doctor_slot_update(getattr(instance, 'doctor_id', None))


@receiver(post_save, sender=DoctorSchedule)
def doctor_schedule_saved(sender, instance, **kwargs):
    _notify_doctor_slot_update(getattr(instance, 'doctor_id', None))


@receiver(post_delete, sender=DoctorSchedule)
def doctor_schedule_deleted(sender, instance, **kwargs):
    _notify_doctor_slot_update(getattr(instance, 'doctor_id', None))
