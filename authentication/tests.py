from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from datetime import date, timedelta
import json

from .models import User, Voter, Admin, InecOfficial
from .serializers import (
    UserSerializer, VoterSerializer, AdminSerializer, InecOfficialSerializer,
    LoginSerializer, RegistrationSerializer
)

User = get_user_model()


class UserModelTest(TestCase):
    """Test User model functionality"""
    
    def setUp(self):
        self.user_data = {
            'name': 'Test User',
            'phone_number': '08123456789',
            'email': 'test@example.com',
            'dob': date(1990, 7, 12),
            'role': 'voter'
        }
    
    def test_create_user(self):
        """Test creating a regular user"""
        user = User.objects.create_user(
            phone_number='08123456789',
            name='Test User',
            password='testpass123'
        )
        self.assertEqual(user.phone_number, '08123456789')
        self.assertEqual(user.name, 'Test User')
        self.assertTrue(user.check_password('testpass123'))
        self.assertEqual(user.role, 'voter')  # Default role
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        admin_user = User.objects.create_superuser(
            phone_number='08123456788',
            name='Admin User',
            password='adminpass123'
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertEqual(admin_user.role, 'admin')
    
    def test_user_string_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(
            phone_number='08123456787',
            name='Test User',
            password='testpass123'
        )
        self.assertEqual(str(user), 'Test User (08123456787)')
    
    def test_unique_phone_number(self):
        """Test phone number uniqueness constraint"""
        User.objects.create_user(
            phone_number='08123456786',
            name='User One',
            password='testpass123'
        )
        
        with self.assertRaises(Exception):
            User.objects.create_user(
                phone_number='08123456786',
                name='User Two',
                password='testpass123'
            )


class VoterModelTest(TestCase):
    """Test Voter model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='08123456785',
            name='Voter User',
            password='testpass123',
            dob=date(1990, 7, 12)
        )
    
    def test_create_voter(self):
        """Test creating a voter profile"""
        voter = Voter.objects.create(
            user=self.user,
            voter_id='TEST123456',
            voters_card_id='VC123456789'
        )
        self.assertEqual(voter.user, self.user)
        self.assertEqual(voter.voter_id, 'TEST123456')
        self.assertEqual(voter.voters_card_id, 'VC123456789')
        self.assertFalse(voter.registration_verified)
        self.assertFalse(voter.can_vote)
    
    def test_voter_verification(self):
        """Test voter verification process"""
        voter = Voter.objects.create(
            user=self.user,
            voter_id='TEST123457'
        )
        
        # Initially not verified
        self.assertFalse(voter.registration_verified)
        self.assertFalse(voter.can_vote)
        
        # After verification
        voter.registration_verified = True
        voter.save()
        
        # Refresh from database
        voter.refresh_from_db()
        self.assertTrue(voter.registration_verified)
    
    def test_unique_voter_id(self):
        """Test voter ID uniqueness constraint"""
        Voter.objects.create(
            user=self.user,
            voter_id='UNIQUE123456'
        )
        
        # Create another user
        user2 = User.objects.create_user(
            phone_number='08123456784',
            name='Another User',
            password='testpass123'
        )
        
        with self.assertRaises(Exception):
            Voter.objects.create(
                user=user2,
                voter_id='UNIQUE123456'  # Same voter_id should fail
            )


class AuthenticationAPITest(APITestCase):
    """Test authentication API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('authentication:register')
        self.login_url = reverse('authentication:login')
        self.logout_url = reverse('authentication:logout')
        self.profile_url = reverse('authentication:profile')
        
        self.valid_registration_data = {
            'name': 'Test User',
            'phone_number': '08123456783',
            'dob': '1990-07-12',
            'voter_id': 'TEST123458',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        }
    
    def test_user_registration_success(self):
        """Test successful user registration"""
        response = self.client.post(
            self.register_url,
            self.valid_registration_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertIn('profile', response.data)
        self.assertEqual(response.data['message'], 
                        'Registration successful! Your account is pending INEC verification.')
        
        # Verify user was created
        self.assertTrue(
            User.objects.filter(phone_number='08123456783').exists()
        )
        
        # Verify voter profile was created
        user = User.objects.get(phone_number='08123456783')
        self.assertTrue(hasattr(user, 'voter'))
        self.assertEqual(user.voter.voter_id, 'TEST123458')
    
    def test_user_registration_duplicate_phone(self):
        """Test registration with duplicate phone number"""
        # Create first user
        self.client.post(self.register_url, self.valid_registration_data, format='json')
        
        # Try to create second user with same phone
        duplicate_data = self.valid_registration_data.copy()
        duplicate_data['voter_id'] = 'DIFF123456'
        
        response = self.client.post(
            self.register_url,
            duplicate_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_user_registration_duplicate_voter_id(self):
        """Test registration with duplicate voter ID"""
        # Create first user
        self.client.post(self.register_url, self.valid_registration_data, format='json')
        
        # Try to create second user with same voter_id
        duplicate_data = self.valid_registration_data.copy()
        duplicate_data['phone_number'] = '08123456782'
        
        response = self.client.post(
            self.register_url,
            duplicate_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_user_registration_underage(self):
        """Test registration with underage user"""
        underage_data = self.valid_registration_data.copy()
        underage_data['dob'] = '2010-07-12'  # Only 14-15 years old
        
        response = self.client.post(
            self.register_url,
            underage_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_user_registration_password_mismatch(self):
        """Test registration with password mismatch"""
        mismatch_data = self.valid_registration_data.copy()
        mismatch_data['password_confirm'] = 'differentpass'
        
        response = self.client.post(
            self.register_url,
            mismatch_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_user_login_success(self):
        """Test successful user login"""
        # First register a user
        self.client.post(self.register_url, self.valid_registration_data, format='json')
        
        # Then try to login
        login_data = {
            'phone_number': '08123456783',
            'password': 'testpass123'
        }
        
        response = self.client.post(
            self.login_url,
            login_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertIn('profile', response.data)
        self.assertEqual(response.data['message'], 'Login successful')
    
    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            'phone_number': '08123456781',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(
            self.login_url,
            login_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_user_logout(self):
        """Test user logout"""
        # Register and login user
        self.client.post(self.register_url, self.valid_registration_data, format='json')
        login_response = self.client.post(
            self.login_url,
            {
                'phone_number': '08123456783',
                'password': 'testpass123'
            },
            format='json'
        )
        
        token = login_response.data['token']
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        
        # Logout
        response = self.client.post(self.logout_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Logout successful')
    
    def test_get_profile_authenticated(self):
        """Test getting user profile when authenticated"""
        # Register and login user
        self.client.post(self.register_url, self.valid_registration_data, format='json')
        login_response = self.client.post(
            self.login_url,
            {
                'phone_number': '08123456783',
                'password': 'testpass123'
            },
            format='json'
        )
        
        token = login_response.data['token']
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        
        # Get profile
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('profile', response.data)
    
    def test_get_profile_unauthenticated(self):
        """Test getting user profile when not authenticated"""
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SerializerTest(TestCase):
    """Test serializers"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='08123456780',
            name='Test User',
            password='testpass123',
            dob=date(1990, 7, 12)
        )
    
    def test_user_serializer(self):
        """Test UserSerializer"""
        serializer = UserSerializer(instance=self.user)
        data = serializer.data
        
        self.assertEqual(data['name'], 'Test User')
        self.assertEqual(data['phone_number'], '08123456780')
        self.assertEqual(data['role'], 'voter')
        self.assertNotIn('password', data)  # Password should not be in serialized data
    
    def test_registration_serializer_valid(self):
        """Test RegistrationSerializer with valid data"""
        data = {
            'name': 'New User',
            'phone_number': '08123456779',
            'dob': '1990-07-12',
            'voter_id': 'NEW123456',
            'password': 'newpass123',
            'password_confirm': 'newpass123'
        }
        
        serializer = RegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_registration_serializer_invalid_voter_id(self):
        """Test RegistrationSerializer with invalid voter ID"""
        data = {
            'name': 'New User',
            'phone_number': '08123456778',
            'dob': '1990-07-12',
            'voter_id': 'INVALID',  # Too short
            'password': 'newpass123',
            'password_confirm': 'newpass123'
        }
        
        serializer = RegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('voter_id', serializer.errors)
    
    def test_login_serializer_valid(self):
        """Test LoginSerializer with valid credentials"""
        data = {
            'phone_number': '08123456780',
            'password': 'testpass123'
        }
        
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['user'], self.user)
    
    def test_login_serializer_invalid(self):
        """Test LoginSerializer with invalid credentials"""
        data = {
            'phone_number': '08123456780',
            'password': 'wrongpassword'
        }
        
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class VoterVerificationTest(APITestCase):
    """Test voter verification functionality"""
    
    def setUp(self):
        # Create INEC official
        self.inec_user = User.objects.create_user(
            phone_number='08123456777',
            name='INEC Official',
            password='inecpass123',
            role='inec_official'
        )
        self.inec_official = InecOfficial.objects.create(
            user=self.inec_user,
            official_id='INEC001'
        )
        self.inec_token = Token.objects.create(user=self.inec_user)
        
        # Create voter
        self.voter_user = User.objects.create_user(
            phone_number='08123456776',
            name='Voter User',
            password='voterpass123',
            dob=date(1990, 7, 12)
        )
        self.voter = Voter.objects.create(
            user=self.voter_user,
            voter_id='VOTER123456'
        )
        
        self.verify_url = reverse(
            'authentication:verify_voter',
            kwargs={'voter_id': 'VOTER123456'}
        )
    
    def test_verify_voter_success(self):
        """Test successful voter verification by INEC official"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.inec_token.key)
        
        response = self.client.post(self.verify_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Check voter is now verified
        self.voter.refresh_from_db()
        self.assertTrue(self.voter.registration_verified)
    
    def test_verify_voter_unauthorized(self):
        """Test voter verification without proper authorization"""
        # Don't set authorization header
        response = self.client.post(self.verify_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_verify_voter_wrong_role(self):
        """Test voter verification with non-INEC user"""
        # Use voter token instead of INEC token
        voter_token = Token.objects.create(user=self.voter_user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + voter_token.key)
        
        response = self.client.post(self.verify_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PhoneNumberValidationTest(TestCase):
    """Test phone number validation"""
    
    def test_valid_phone_numbers(self):
        """Test various valid phone number formats"""
        valid_numbers = [
            '08123456775',
            '07012345678',
            '09087654321',
            '+2348123456774'
        ]
        
        for i, phone in enumerate(valid_numbers):
            user = User.objects.create_user(
                phone_number=phone,
                name=f'User {i}',
                password='testpass123'
            )
            self.assertIsNotNone(user)
    
    def test_phone_number_normalization(self):
        """Test phone number normalization"""
        data = {
            'name': 'Test User',
            'phone_number': '0812 345 6773',  # With spaces
            'dob': '1990-07-12',
            'voter_id': 'NORM123456',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        }
        
        serializer = RegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        # Phone number should be normalized (spaces removed)
        normalized_phone = serializer.validated_data['phone_number']
        self.assertEqual(normalized_phone, '08123456773')


class AgeValidationTest(TestCase):
    """Test age validation for voter registration"""
    
    def test_valid_age(self):
        """Test registration with valid age (18+)"""
        birth_date = date.today() - timedelta(days=365 * 20)  # 20 years old
        
        data = {
            'name': 'Adult User',
            'phone_number': '08123456772',
            'dob': birth_date.strftime('%Y-%m-%d'),
            'voter_id': 'ADULT123456',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        }
        
        serializer = RegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_invalid_age(self):
        """Test registration with invalid age (under 18)"""
        birth_date = date.today() - timedelta(days=365 * 16)  # 16 years old
        
        data = {
            'name': 'Minor User',
            'phone_number': '08123456771',
            'dob': birth_date.strftime('%Y-%m-%d'),
            'voter_id': 'MINOR123456',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        }
        
        serializer = RegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('dob', serializer.errors)
    
    def test_edge_case_exactly_18(self):
        """Test registration exactly on 18th birthday"""
        birth_date = date.today() - timedelta(days=365 * 18)  # Exactly 18 years ago
        
        data = {
            'name': 'Eighteen User',
            'phone_number': '08123456770',
            'dob': birth_date.strftime('%Y-%m-%d'),
            'voter_id': 'EIGHT123456',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        }
        
        serializer = RegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
