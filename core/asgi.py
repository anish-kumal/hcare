"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application
from apps.appointments.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django_asgi_app = get_asgi_application()

# Wrap only HTTP requests to serve collected static assets reliably.
if not settings.DEBUG:
    django_asgi_app = ASGIStaticFilesHandler(django_asgi_app)

# Ensure a default superuser exists when the ASGI app starts (useful when
# starting with `daphne core.asgi:application`). This is guarded so that if
# the database or migrations aren't ready we won't crash the process.
try:
    # Import here so Django is already configured by get_asgi_application()
    from django.contrib.auth import get_user_model
    from django.core.management import call_command

    User = get_user_model()
    # Only create if there's no superuser at all. This avoids overwriting or
    # changing any existing admin accounts.
    if not User.objects.filter(is_superuser=True).exists():
        # Call the existing management command which respects env vars and
        # default values.
        try:
            call_command("create_default_superuser", verbosity=0)
        except Exception:
            # If calling the management command fails for any reason, fall
            # back to a safe direct creation attempt and let errors be
            # handled below.
            User.objects.create_superuser(
                username="anish",
                email="hcare0139@gmail.com",
                password="Github.com1",
            )
except Exception as exc:
    # Don't prevent the ASGI app from starting; log and continue. Common
    # failures include database not ready or migrations missing.
    import logging

    logging.getLogger(__name__).warning(
        "Default superuser check/create skipped or failed: %s", exc
    )

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
