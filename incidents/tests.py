from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from datetime import timedelta, date
import uuid

from .models import IncidentReport, IncidentEvidence, IncidentResponse
from authentication.models import User, Voter, InecOfficial

User = get_user_model()


class IncidentModelTest(TestCase):
    """Test incident models"""
    
    def setUp(self):
        # Create users
        self.reporter_user = User._default_manager.create_user(
            phone_number='08123456790',
            name='Reporter User',
            password='testpass123',
            dob=date(1990, 1, 1)
        )
        
        self.voter_user = User._default_manager.create_user(
            phone_number='08123456791',
            name='Voter User',
            password='testpass123',
            dob=date(1990, 1, 1)
        )
        self.voter = Voter._default_manager.create(
            user=self.voter_user,
            voter_id='VOTER00003',
            registration_verified=True
        )
        
        self.inec_user = User._default_manager.create_user(
            phone_number='08123456792',
            name='INEC User',
            password='testpass123',
            role='inec_official'
        )
        self.inec_official = InecOfficial._default_manager.create(
            user=self.inec_user,
            official_id='INEC003'
        )
    
    def test_create_incident_report(self):
        """Test creating an incident report"""
        incident = IncidentReport._default_manager.create(
            reporter=self.reporter_user,
            voter=self.voter,
            incident_type='voter_intimidation',
            description='Voter was intimidated at polling station',
            location='Lagos Main Polling Station',
            priority='high'
        )
        
        self.assertEqual(incident.reporter, self.reporter_user)
        self.assertEqual(incident.voter, self.voter)
        self.assertEqual(incident.incident_type, 'voter_intimidation')
        self.assertEqual(incident.status, 'pending')
        self.assertEqual(incident.priority, 'high')
    
    def test_create_incident_evidence(self):
        """Test creating incident evidence"""
        incident = IncidentReport._default_manager.create(
            reporter=self.reporter_user,
            voter=self.voter,
            incident_type='ballot_stuffing',
            description='Ballot box was stuffed with fake ballots',
            location='Abuja Central Polling Station'
        )
        
        evidence = IncidentEvidence._default_manager.create(
            incident=incident,
            evidence_type='photo',
            description='Photo evidence of ballot stuffing'
        )
        
        self.assertEqual(evidence.incident, incident)
        self.assertEqual(evidence.evidence_type, 'photo')
    
    def test_create_incident_response(self):
        """Test creating incident response"""
        incident = IncidentReport._default_manager.create(
            reporter=self.reporter_user,
            voter=self.voter,
            incident_type='technical_issue',
            description='Voting machine malfunction',
            location='Port Harcourt Polling Station'
        )
        
        response = IncidentResponse._default_manager.create(
            incident=incident,
            responder=self.inec_official,
            action_type='investigation_started',
            description='Investigation team dispatched to location'
        )
        
        self.assertEqual(response.incident, incident)
        self.assertEqual(response.responder, self.inec_official)
        self.assertEqual(response.action_type, 'investigation_started')


class IncidentAPITest(APITestCase):
    """Test incident API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.reporter_user = User._default_manager.create_user(
            phone_number='08123456793',
            name='Reporter User',
            password='testpass123',
            dob=date(1990, 1, 1)
        )
        self.reporter_token = Token.objects.create(user=self.reporter_user)
        
        self.voter_user = User._default_manager.create_user(
            phone_number='08123456794',
            name='Voter User',
            password='testpass123',
            dob=date(1990, 1, 1)
        )
        self.voter = Voter._default_manager.create(
            user=self.voter_user,
            voter_id='VOTER00004',
            registration_verified=True
        )
        self.voter_token = Token.objects.create(user=self.voter_user)
        
        self.inec_user = User._default_manager.create_user(
            phone_number='08123456795',
            name='INEC User',
            password='testpass123',
            role='inec_official'
        )
        self.inec_official = InecOfficial._default_manager.create(
            user=self.inec_user,
            official_id='INEC004'
        )
        self.inec_token = Token.objects.create(user=self.inec_user)
        
        # Create incident
        self.incident = IncidentReport._default_manager.create(
            reporter=self.reporter_user,
            voter=self.voter,
            incident_type='voter_intimidation',
            description='Voter was intimidated at polling station',
            location='Lagos Main Polling Station',
            priority='high'
        )
    
    def test_create_incident_report(self):
        """Test creating an incident report via API"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.voter_token.key)
        
        data = {
            'incident_type': 'ballot_stuffing',
            'description': 'Ballot box was stuffed with fake ballots',
            'location': 'Abuja Central Polling Station',
            'priority': 'critical'
        }
        
        response = self.client.post('/api/incidents/reports/', data, format='json')
        
        # For testing, we'll check the most common attributes
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('incident_type', response.data)
        
        # Verify incident was created
        self.assertTrue(IncidentReport._default_manager.filter(
            reporter=self.voter_user,
            incident_type='ballot_stuffing'
        ).exists())
    
    def test_get_incident_reports(self):
        """Test getting incident reports"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.reporter_token.key)
        
        response = self.client.get('/api/incidents/reports/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_assign_incident(self):
        """Test assigning incident to INEC official"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.inec_token.key)
        
        data = {
            'incident_id': str(self.incident.report_id),
            'official_id': str(self.inec_official.user.user_id)
        }
        
        response = self.client.post('/api/incidents/assign/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify incident was assigned
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.assigned_to, self.inec_official)
        self.assertEqual(self.incident.status, 'investigating')
    
    def test_update_incident_status(self):
        """Test updating incident status"""
        # First assign the incident
        self.incident.assign_to_official(self.inec_official)
        
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.inec_token.key)
        
        data = {
            'status': 'resolved',
            'resolution_notes': 'Incident investigated and resolved'
        }
        
        response = self.client.post(f'/api/incidents/reports/{self.incident.report_id}/status/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify status was updated
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, 'resolved')
        self.assertEqual(self.incident.resolution_notes, 'Incident investigated and resolved')
    
    def test_add_incident_response(self):
        """Test adding response to incident"""
        # First assign the incident
        self.incident.assign_to_official(self.inec_official)
        
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.inec_token.key)
        
        data = {
            'incident': str(self.incident.report_id),
            'action_type': 'investigation_started',
            'description': 'Investigation team dispatched to location'
        }
        
        response = self.client.post('/api/incidents/response/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('response_id', response.data)
        
        # Verify response was created
        self.assertTrue(IncidentResponse._default_manager.filter(
            incident=self.incident,
            responder=self.inec_official,
            action_type='investigation_started'
        ).exists())
    
    def test_get_my_incidents(self):
        """Test getting incidents reported by current user"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.reporter_token.key)
        
        response = self.client.get('/api/incidents/my-incidents/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['report_id'], str(self.incident.report_id))
    
    def test_incident_stats(self):
        """Test getting incident statistics"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.inec_token.key)
        
        response = self.client.get('/api/incidents/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_incidents', response.data)
        self.assertIn('incidents_by_status', response.data)