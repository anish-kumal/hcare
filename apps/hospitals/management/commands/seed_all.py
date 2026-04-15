"""Seed initial hospital, admin, doctors and schedules.

Usage:
  python manage.py seed_all

This command is idempotent and will skip creating objects that already exist.
"""

from uuid import uuid4
from datetime import date, time
import random

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from apps.hospitals.models import Hospital, HospitalAdmin
from apps.doctors.models import Doctor, DoctorSchedule


User = get_user_model()


class Command(BaseCommand):
    help = "Seed hospital, admin, doctors and schedules (idempotent)."

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write("Seeding data...")

            # 1) Create or get hospital
            hospital_name = "Royal Hospital"
            hospital_email = "contact@royal-hospital.example"
            reg_no = f"RH-{uuid4().hex[:8].upper()}"

            hospital, created = Hospital.objects.get_or_create(
                name=hospital_name,
                defaults={
                    "registration_number": reg_no,
                    "email": hospital_email,
                    "phone_number": "+977-1-5555555",
                    "address": "Some street, Kathmandu",
                    "city": "Kathmandu",
                    "state": "Bagmati",
                    "country": "Nepal",
                    "total_beds": 150,
                    "is_verified": True,
                    "verified_at": timezone.now(),
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created hospital: {hospital.name}")
                )
            else:
                # Ensure verified flags are set
                updated = False
                if not hospital.is_verified:
                    hospital.is_verified = True
                    hospital.verified_at = timezone.now()
                    updated = True
                if updated:
                    hospital.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Updated hospital verification: {hospital.name}"
                        )
                    )
                else:
                    self.stdout.write(f"Hospital already exists: {hospital.name}")

            # Try to pick a superuser as verifier if available
            verifier = User.objects.filter(is_superuser=True).first()
            if verifier and hospital.verified_by is None:
                hospital.verified_by = verifier
                hospital.save()

            # 2) Create hospital admin user and HospitalAdmin relation
            admin_username = "admin"
            admin_email = "admin@royal-hospital.gmail.com"
            admin_password = "Github.com1"

            admin_user, au_created = User.objects.get_or_create(
                username=admin_username,
                defaults={
                    "email": admin_email,
                },
            )

            if au_created:
                admin_user.set_password(admin_password)
                admin_user.user_type = admin_user.UserType.ADMIN
                admin_user.is_staff = True
                admin_user.is_active = True
                # mark that the admin is not using a default password
                admin_user.is_default_password = False
                admin_user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created hospital admin user: {admin_user.username}"
                    )
                )
            else:
                self.stdout.write(f"Hospital admin user exists: {admin_user.username}")

            # Create HospitalAdmin relation if missing
            ha, ha_created = HospitalAdmin.objects.get_or_create(
                user=admin_user,
                hospital=hospital,
            )
            if ha_created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Linked admin {admin_user.username} to hospital {hospital.name}"
                    )
                )

            # 3) Create 9 doctors with profiles and schedules
            specializations = [
                "General Medicine",
                "Pediatrics",
                "Orthopedics",
                "Cardiology",
                "Dermatology",
                "ENT",
                "Ophthalmology",
                "Gynecology",
                "Neurology",
            ]

            created_doctors = []

            for i in range(1, 10):
                username = f"doctor{i}"
                email = f"doctor{i}@royal-hospital.example"
                password = "doctorpass123"

                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                    },
                )

                if user_created:
                    user.set_password(password)
                    user.user_type = user.UserType.DOCTOR
                    user.is_active = True
                    # doctors created here will keep default-password marker True
                    user.is_default_password = True
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f"Created user {username}"))
                else:
                    self.stdout.write(f"User exists: {username}")

                # create or get Doctor profile
                spec = specializations[(i - 1) % len(specializations)]
                license_no = f"LIC-{uuid4().hex[:8].upper()}"
                emp_id = f"EMP-{1000 + i}"

                doctor, doc_created = Doctor.objects.get_or_create(
                    user=user,
                    defaults={
                        "hospital": hospital,
                        "department": None,
                        "specialization": spec,
                        "license_number": license_no,
                        "employee_id": emp_id,
                        "qualification": "MBBS",
                        "experience_years": random.randint(1, 15),
                        "joining_date": date.today(),
                        "consultation_fee": 500.00,
                    },
                )

                if doc_created:
                    created_doctors.append(doctor)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created doctor profile for {user.username}: {spec}"
                        )
                    )
                else:
                    self.stdout.write(f"Doctor profile exists for {user.username}")

                # Assign a profile picture public id in the Cloudinary folder
                try:
                    doctor.profile_picture = (
                        f"health_care/doctors/profiles/{user.username}.jpg"
                    )
                    doctor.save()
                except Exception:
                    # If Cloudinary isn't configured, ignore and continue
                    pass

                # create varied schedules: each doctor gets 2-5 weekdays with
                # 1-2 sessions per selected weekday. This creates more realistic
                # and differing availability per doctor.
                weekdays = random.sample(range(0, 7), k=random.randint(2, 5))
                for weekday in weekdays:
                    # decide number of sessions that day (1 or 2)
                    sessions = random.choice([1, 2])
                    possible_slots = [
                        (8, 11),  # morning 8-11
                        (9, 12),  # morning 9-12
                        (10, 13),
                        (13, 16),  # afternoon 13-16
                        (14, 17),  # afternoon 14-17
                        (15, 18),
                    ]

                    chosen = random.sample(possible_slots, k=sessions)
                    for start_h, end_h in chosen:
                        st = time(start_h, 0)
                        et = time(end_h, 0)
                        try:
                            schedule, sched_created = (
                                DoctorSchedule.objects.get_or_create(
                                    doctor=doctor,
                                    weekday=weekday,
                                    start_time=st,
                                    end_time=et,
                                    defaults={
                                        "slot_duration": random.choice([15, 20, 30]),
                                        "max_patients": random.choice([10, 15, 20]),
                                        "is_available": True,
                                    },
                                )
                            )
                            # ensure time_slots are calculated and saved
                            if sched_created:
                                schedule.save()
                            else:
                                # update slot_duration if needed and recalc
                                schedule.time_slots = schedule._calculate_time_slots()
                                schedule.save()
                        except Exception:
                            # ignore conflicts or validation errors and continue
                            pass

            self.stdout.write(
                self.style.SUCCESS(
                    f"Seed complete. Doctors created/checked: {len(created_doctors)}"
                )
            )
