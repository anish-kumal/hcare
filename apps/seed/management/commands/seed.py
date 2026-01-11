from datetime import date, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.users.models import User
from apps.hospitals.models import Hospital, HospitalAdmin, HospitalDepartment
from apps.doctors.models import Doctor, DoctorSchedule, Specialization
from apps.patients.models import Patient, PatientAppointment
from apps.otp.models import OTP


class Command(BaseCommand):
    help = 'Seed the database with sample data for all models'

    def handle(self, *args, **options):
        total_records = 120

        super_admin = self._ensure_user(
            username='superadmin',
            email='superadmin@healthcare.test',
            user_type=User.UserType.SUPER_ADMIN,
            first_name='Super',
            last_name='Admin',
            password='Admin@123',
            is_staff=True,
            is_superuser=True,
        )

        hospitals = []
        departments = []
        specializations = []
        doctors = []
        patients = []

        for index in range(1, total_records + 1):
            specialization, _ = Specialization.objects.update_or_create(
                code=f'SPEC-{index:03d}',
                defaults={
                    'name': f'Specialization {index:03d}',
                    'description': f'Description for specialization {index:03d}.',
                },
            )
            specializations.append(specialization)

        for index in range(1, total_records + 1):
            hospital, _ = Hospital.objects.update_or_create(
                registration_number=f'HOSP-{index:03d}',
                defaults={
                    'name': f'Health Care Hospital {index:03d}',
                    'email': f'hospital{index:03d}@healthcare.test',
                    'phone_number': f'555-{1000 + index}',
                    'address': f'Main Street {100 + index}',
                    'city': 'Kathmandu',
                    'state': 'Bagmati',
                    'country': 'Nepal',
                    'postal_code': f'{44000 + index}',
                    'description': f'Primary healthcare facility {index:03d}.',
                    'total_beds': 100 + index,
                    'emergency_contact': f'555-{2000 + index}',
                    'is_verified': True,
                    'verified_at': timezone.now(),
                    'verified_by': super_admin,
                },
            )
            hospitals.append(hospital)

            department, _ = HospitalDepartment.objects.update_or_create(
                hospital=hospital,
                code=f'DEP-{index:03d}',
                defaults={
                    'name': f'Department {index:03d}',
                    'description': f'Department description {index:03d}.',
                    'total_beds': 20 + (index % 30),
                    'available_beds': 10 + (index % 10),
                    'head_doctor': None,
                },
            )
            departments.append(department)

        for index in range(1, total_records + 1):
            admin_user = self._ensure_user(
                username=f'admin{index:03d}',
                email=f'admin{index:03d}@healthcare.test',
                user_type=User.UserType.ADMIN,
                first_name='Admin',
                last_name=f'User{index:03d}',
                password='Admin@123',
                is_staff=True,
                is_superuser=False,
            )

            HospitalAdmin.objects.update_or_create(
                user=admin_user,
                defaults={
                    'hospital': hospitals[index - 1],
                    'designation': 'Hospital Administrator',
                    'employee_id': f'ADM-{index:04d}',
                    'department': 'Operations',
                    'joining_date': date(2023, 1, 1) + timedelta(days=index),
                    'permissions': {'manage_users': True, 'manage_departments': True},
                },
            )

        for index in range(1, total_records + 1):
            doctor_user = self._ensure_user(
                username=f'doctor{index:03d}',
                email=f'doctor{index:03d}@healthcare.test',
                user_type=User.UserType.DOCTOR,
                first_name='Doctor',
                last_name=f'User{index:03d}',
                password='Doctor@123',
                is_staff=False,
                is_superuser=False,
            )

            doctor, _ = Doctor.objects.update_or_create(
                user=doctor_user,
                defaults={
                    'hospital': hospitals[index - 1],
                    'department': departments[index - 1],
                    'specialization': specializations[index - 1],
                    'license_number': f'LIC-{index:04d}',
                    'employee_id': f'DOC-{index:04d}',
                    'qualification': 'MBBS, MD',
                    'experience_years': 3 + (index % 12),
                    'bio': f'Doctor profile for seed {index:03d}.',
                    'consultation_fee': 400.00 + (index % 100),
                    'is_available': True,
                    'is_verified': True,
                    'verified_at': timezone.now(),
                    'verified_by': super_admin,
                    'joining_date': date(2022, 1, 1) + timedelta(days=index),
                },
            )
            doctor.additional_specializations.set([
                specializations[(index - 1) % total_records],
                specializations[(index + 1) % total_records],
            ])
            doctors.append(doctor)

            department = departments[index - 1]
            department.head_doctor = doctor_user
            department.save(update_fields=['head_doctor'])

            for weekday, start_hour, duration in [(0, 9, 30), (2, 13, 20), (4, 16, 15)]:
                DoctorSchedule.objects.update_or_create(
                    doctor=doctor,
                    weekday=weekday,
                    start_time=time(start_hour, 0),
                    defaults={
                        'end_time': time(start_hour + 3, 0),
                        'slot_duration': duration,
                        'max_patients': 12 + (index % 10),
                        'is_available': True,
                    },
                )

        for index in range(1, total_records + 1):
            patient_user = self._ensure_user(
                username=f'patient{index:03d}',
                email=f'patient{index:03d}@healthcare.test',
                user_type=User.UserType.PATIENT,
                first_name='Patient',
                last_name=f'User{index:03d}',
                password='Patient@123',
                is_staff=False,
                is_superuser=False,
            )

            patient, _ = Patient.objects.update_or_create(
                user=patient_user,
                defaults={
                    'hospital': hospitals[index - 1],
                    'doctor': doctors[index - 1],
                    'date_of_birth': date(1985, 1, 1) + timedelta(days=index * 10),
                    'gender': 'F' if index % 2 == 0 else 'M',
                    'blood_group': 'A+' if index % 2 == 0 else 'O+',
                    'contact_number': f'555-{3000 + index}',
                    'emergency_contact': f'555-{4000 + index}',
                    'emergency_contact_name': f'Contact {index:03d}',
                    'address': f'Patient Street {index:03d}',
                    'city': 'Kathmandu',
                    'state': 'Bagmati',
                    'country': 'Nepal',
                    'postal_code': f'{45000 + index}',
                    'medical_history': 'No known allergies.',
                    'insurance_provider': 'HealthPlus',
                    'insurance_policy_number': f'HP-2024-{index:03d}',
                    'is_verified': True,
                    'verified_at': timezone.now(),
                },
            )
            patients.append(patient)

            appointment_date = date.today() + timedelta(days=index % 21)
            appointment_time = time(8 + (index % 9), 0)
            PatientAppointment.objects.update_or_create(
                patient=patient,
                doctor=doctors[index - 1],
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                defaults={
                    'status': 'CONFIRMED',
                    'reason': f'Routine checkup {index:03d}',
                    'notes': 'Seeded appointment.',
                },
            )

            OTP.objects.update_or_create(
                user=patient_user,
                defaults={
                    'code': f'{index % 1000000:06d}',
                    'expires_at': timezone.now() + timedelta(minutes=10),
                    'verified': False,
                    'attempts': 0,
                },
            )

        self.stdout.write(self.style.SUCCESS('Seed data created successfully.'))

    def _ensure_user(self, username, email, user_type, first_name, last_name, password, is_staff, is_superuser):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'user_type': user_type,
                'first_name': first_name,
                'last_name': last_name,
                'is_staff': is_staff,
                'is_superuser': is_superuser,
            },
        )

        if not created:
            user.email = email
            user.user_type = user_type
            user.first_name = first_name
            user.last_name = last_name
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save()
        else:
            user.set_password(password)
            user.save()

        return user
