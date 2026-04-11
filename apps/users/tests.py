from django.test import TestCase, override_settings
from django.urls import reverse

from axes.models import AccessAttempt

from .models import User


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)
class AxesLockListViewTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_superuser(
            username='superadmin',
            email='superadmin@example.com',
            password='CorrectPass123!',
        )

        AccessAttempt.objects.create(
            username='locked_user',
            ip_address='127.0.0.1',
            user_agent='pytest',
            http_accept='text/html',
            path_info='/auth/login/',
            get_data='',
            post_data='',
            failures_since_start=5,
        )

        AccessAttempt.objects.create(
            username='locked_user',
            ip_address='127.0.0.2',
            user_agent='pytest',
            http_accept='text/html',
            path_info='/auth/administer/login/',
            get_data='',
            post_data='',
            failures_since_start=5,
        )

    def test_super_admin_can_view_axes_lock_list(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(reverse('users:axes_lock_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Axes Lockouts')
        self.assertContains(response, 'locked_user')
        self.assertContains(response, 'Unlock')

    def test_super_admin_can_unlock_locked_user(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(reverse('users:axes_unlock_user', kwargs={'username': 'locked_user'}), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Unlocked locked_user successfully.')
        self.assertEqual(AccessAttempt.objects.filter(username='locked_user').count(), 0)
