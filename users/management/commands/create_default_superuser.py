"""Django management command to create or update a default superuser.

This command uses environment variables when present:
 - DJANGO_SUPERUSER_USERNAME (default: "anish")
 - DJANGO_SUPERUSER_EMAIL (default: "hcare0139@gmail.com")
 - DJANGO_SUPERUSER_PASSWORD (default: "Github.com1")

It can also be called with `--username`, `--email`, `--password` overrides.

Usage:
    python manage.py create_default_superuser
    # or with custom values
    python manage.py create_default_superuser --username foo --email foo@ex.com --password secret
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
import os


class Command(BaseCommand):
    help = "Create or update a default superuser from env vars or provided options."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=os.environ.get("DJANGO_SUPERUSER_USERNAME", "anish"),
            help="Username for the superuser (or set DJANGO_SUPERUSER_USERNAME)",
        )
        parser.add_argument(
            "--email",
            default=os.environ.get("DJANGO_SUPERUSER_EMAIL", "hcare0139@gmail.com"),
            help="Email for the superuser (or set DJANGO_SUPERUSER_EMAIL)",
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Github.com1"),
            help="Password for the superuser (or set DJANGO_SUPERUSER_PASSWORD)",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if not username:
            self.stderr.write(self.style.ERROR("A username is required."))
            return

        with transaction.atomic():
            user_qs = User.objects.filter(username=username)
            if user_qs.exists():
                user = user_qs.first()
                user.email = email or user.email
                user.is_staff = True
                user.is_superuser = True
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated existing superuser "{username}"')
                )
            else:
                # create_superuser handles any custom user model requirements
                try:
                    User.objects.create_superuser(
                        username=username, email=email, password=password
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'Created superuser "{username}"')
                    )
                except TypeError:
                    # Some custom user models use email as the USERNAME_FIELD
                    # Try creating using email as the identifier
                    try:
                        User.objects.create_superuser(email=email, password=password)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created superuser with email "{email}"'
                            )
                        )
                    except Exception as exc:
                        self.stderr.write(
                            self.style.ERROR(f"Failed to create superuser: {exc}")
                        )
