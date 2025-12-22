from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from .models import OTP
from .services import OTPService

User = get_user_model()


class OTPModelTestCase(TestCase):
    """Test cases for OTP model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_otp_creation(self):
        """Test OTP model creation"""
        otp = OTP.objects.create(
            user=self.user,
            code='123456',
            expires_at=timezone.now() + timedelta(minutes=5),
            verified=False
        )
        self.assertEqual(otp.user, self.user)
        self.assertEqual(otp.code, '123456')
        self.assertFalse(otp.verified)
    
    def test_is_expired(self):
        """Test is_expired property"""
        # Not expired OTP
        otp = OTP.objects.create(
            user=self.user,
            code='123456',
            expires_at=timezone.now() + timedelta(minutes=5),
            verified=False
        )
        self.assertFalse(otp.is_expired)
        
        # Expired OTP
        expired_otp = OTP.objects.create(
            user=User.objects.create_user(
                username='testuser2',
                email='test2@example.com',
                password='testpass123'
            ),
            code='654321',
            expires_at=timezone.now() - timedelta(minutes=1),
            verified=False
        )
        self.assertTrue(expired_otp.is_expired)
    
    def test_is_valid(self):
        """Test is_valid property"""
        otp = OTP.objects.create(
            user=self.user,
            code='123456',
            expires_at=timezone.now() + timedelta(minutes=5),
            verified=False
        )
        self.assertTrue(otp.is_valid)
        
        otp.verified = True
        otp.save()
        self.assertFalse(otp.is_valid)
    
    def test_verify(self):
        """Test verify method"""
        otp = OTP.objects.create(
            user=self.user,
            code='123456',
            expires_at=timezone.now() + timedelta(minutes=5),
            verified=False
        )
        result = otp.verify()
        self.assertTrue(result)
        otp.refresh_from_db()
        self.assertTrue(otp.verified)
        self.assertIsNotNone(otp.verified_at)
    
    def test_verify_expired_otp(self):
        """Test verify on expired OTP"""
        otp = OTP.objects.create(
            user=self.user,
            code='123456',
            expires_at=timezone.now() - timedelta(minutes=1),
            verified=False
        )
        result = otp.verify()
        self.assertFalse(result)
        otp.refresh_from_db()
        self.assertFalse(otp.verified)
    
    def test_increment_attempts(self):
        """Test increment_attempts method"""
        otp = OTP.objects.create(
            user=self.user,
            code='123456',
            expires_at=timezone.now() + timedelta(minutes=5),
            attempts=0
        )
        otp.increment_attempts()
        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 1)


class OTPServiceTestCase(TestCase):
    """Test cases for OTPService"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_generate_code(self):
        """Test OTP code generation"""
        code = OTPService.generate_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
    
    def test_calculate_expiry(self):
        """Test expiry calculation"""
        now = timezone.now()
        expiry = OTPService.calculate_expiry()
        self.assertGreater(expiry, now)
        # Should be approximately 5 minutes from now
        time_diff = (expiry - now).total_seconds()
        self.assertAlmostEqual(time_diff, 300, delta=5)
    
    def test_create_or_update(self):
        """Test OTP creation"""
        otp = OTPService.create_or_update(self.user)
        self.assertEqual(otp.user, self.user)
        self.assertEqual(len(otp.code), 6)
        self.assertFalse(otp.verified)
        self.assertEqual(otp.attempts, 0)
    
    def test_create_or_update_existing(self):
        """Test OTP update"""
        otp1 = OTPService.create_or_update(self.user)
        code1 = otp1.code
        
        otp2 = OTPService.create_or_update(self.user)
        code2 = otp2.code
        
        # Same user, should update
        self.assertEqual(otp1.user_id, otp2.user_id)
        self.assertNotEqual(code1, code2)
    
    def test_verify_code_success(self):
        """Test successful code verification"""
        otp = OTPService.create_or_update(self.user)
        success, message = OTPService.verify_code(self.user, otp.code)
        self.assertTrue(success)
        self.assertIn('verified successfully', message)
    
    def test_verify_code_invalid(self):
        """Test invalid code verification"""
        OTPService.create_or_update(self.user)
        success, message = OTPService.verify_code(self.user, '000000')
        self.assertFalse(success)
        self.assertIn('Invalid OTP', message)
    
    def test_verify_code_no_otp(self):
        """Test verification when no OTP exists"""
        success, message = OTPService.verify_code(self.user, '123456')
        self.assertFalse(success)
        self.assertIn('No OTP found', message)
    
    def test_verify_code_already_verified(self):
        """Test verification of already verified OTP"""
        otp = OTPService.create_or_update(self.user)
        OTPService.verify_code(self.user, otp.code)
        
        success, message = OTPService.verify_code(self.user, otp.code)
        self.assertFalse(success)
        self.assertIn('already verified', message)
    
    def test_max_attempts(self):
        """Test maximum attempts limit"""
        otp = OTPService.create_or_update(self.user)
        
        for i in range(5):
            success, _ = OTPService.verify_code(self.user, '000000')
            self.assertFalse(success)
        
        # 6th attempt should fail with max attempts message
        success, message = OTPService.verify_code(self.user, '000000')
        self.assertFalse(success)
        self.assertIn('Maximum attempts exceeded', message)
    
    def test_resend_otp(self):
        """Test OTP resend"""
        otp1 = OTPService.create_or_update(self.user)
        otp2, _ = OTPService.resend_otp(self.user)
        
        self.assertNotEqual(otp1.code, otp2.code)
        self.assertEqual(otp2.attempts, 0)
    
    def test_delete_verified_otp(self):
        """Test deletion of verified OTP"""
        otp = OTPService.create_or_update(self.user)
        OTPService.verify_code(self.user, otp.code)
        
        deleted = OTPService.delete_verified_otp(self.user)
        self.assertTrue(deleted)
        
        with self.assertRaises(OTP.DoesNotExist):
            OTP.objects.get(user=self.user)


class OTPViewTestCase(TestCase):
    """Test cases for OTP views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_request_otp_view_get(self):
        """Test OTP request view GET"""
        response = self.client.get('/otp/request/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'otp/request_otp.html')
    
    def test_request_otp_view_post(self):
        """Test OTP request view POST"""
        response = self.client.post('/otp/request/', {
            'email': self.user.email
        })
        # Should redirect to verify view
        self.assertEqual(response.status_code, 302)
    
    def test_request_otp_view_invalid_email(self):
        """Test OTP request with invalid email"""
        response = self.client.post('/otp/request/', {
            'email': 'nonexistent@example.com'
        })
        self.assertEqual(response.status_code, 200)
    
    def test_verify_otp_view_get(self):
        """Test OTP verify view GET"""
        response = self.client.get(f'/otp/verify/{self.user.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'otp/verify_otp.html')
    
    def test_verify_otp_view_post(self):
        """Test OTP verify view POST"""
        otp_instance = OTPService.create_or_update(self.user)
        response = self.client.post(f'/otp/verify/{self.user.id}/', {
            'otp_code': otp_instance.code
        })
        self.assertEqual(response.status_code, 302)

