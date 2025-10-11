from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from datetime import timedelta, date
import uuid

from .models import Vote, VotingSession, Ballot, BallotCandidate
from elections.models import Election, Candidate
from authentication.models import User, Voter, InecOfficial

User = get_user_model()


class VotingModelTest(TestCase):
    """Test voting models"""
    
    def setUp(self):
        # Create users
        self.voter_user = User.objects.create_user(
            phone_number='08123456780',
            name='Voter User',
            password='testpass123',
            dob=date(1990, 1, 1)
        )
        self.voter = Voter.objects.create(
            user=self.voter_user,
            voter_id='VOTER00001',
            registration_verified=True
        )
        
        self.inec_user = User.objects.create_user(
            phone_number='08123456781',
            name='INEC User',
            password='testpass123',
            role='inec_official'
        )
        self.inec_official = InecOfficial.objects.create(
            user=self.inec_user,
            official_id='INEC001'
        )
        
        # Create election
        self.election = Election.objects.create(
            title='Test Election',
            type='presidential',
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
            status='ongoing',
            created_by=self.inec_official
        )
        
        # Create candidates
        self.candidate1 = Candidate.objects.create(
            name='Candidate 1',
            party='Party A',
            position='President',
            election=self.election
        )
        
        self.candidate2 = Candidate.objects.create(
            name='Candidate 2',
            party='Party B',
            position='President',
            election=self.election
        )
    
    def test_create_vote(self):
        """Test creating a vote"""
        vote = Vote.objects.create(
            voter=self.voter,
            election=self.election,
            candidate=self.candidate1
        )
        
        self.assertEqual(vote.voter, self.voter)
        self.assertEqual(vote.election, self.election)
        self.assertEqual(vote.candidate, self.candidate1)
        self.assertFalse(vote.is_verified)
    
    def test_create_voting_session(self):
        """Test creating a voting session"""
        session = VotingSession.objects.create(
            voter=self.voter,
            election=self.election,
            ip_address='127.0.0.1',
            user_agent='Test Browser'
        )
        
        self.assertEqual(session.voter, self.voter)
        self.assertEqual(session.election, self.election)
        self.assertEqual(session.status, 'started')
        self.assertEqual(session.ip_address, '127.0.0.1')
    
    def test_create_ballot(self):
        """Test creating a ballot"""
        ballot = Ballot.objects.create(election=self.election)
        
        # Add candidates to ballot
        BallotCandidate.objects.create(
            ballot=ballot,
            candidate=self.candidate1,
            order=1
        )
        BallotCandidate.objects.create(
            ballot=ballot,
            candidate=self.candidate2,
            order=2
        )
        
        self.assertEqual(ballot.election, self.election)
        self.assertEqual(ballot.ballotcandidate_set.count(), 2)
    
    def test_vote_unique_constraint(self):
        """Test that a voter can only vote once per election"""
        # Create first vote
        Vote.objects.create(
            voter=self.voter,
            election=self.election,
            candidate=self.candidate1
        )
        
        # Try to create second vote for same voter and election
        with self.assertRaises(Exception):
            Vote.objects.create(
                voter=self.voter,
                election=self.election,
                candidate=self.candidate2
            )


class VotingAPITest(APITestCase):
    """Test voting API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.voter_user = User.objects.create_user(
            phone_number='08123456782',
            name='Voter User',
            password='testpass123',
            dob=date(1990, 1, 1)
        )
        self.voter = Voter.objects.create(
            user=self.voter_user,
            voter_id='VOTER00002',
            registration_verified=True
        )
        self.voter_token = Token.objects.create(user=self.voter_user)
        
        self.inec_user = User.objects.create_user(
            phone_number='08123456783',
            name='INEC User',
            password='testpass123',
            role='inec_official'
        )
        self.inec_official = InecOfficial.objects.create(
            user=self.inec_user,
            official_id='INEC002'
        )
        
        # Create election
        self.election = Election.objects.create(
            title='Test Election',
            type='presidential',
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
            status='ongoing',
            created_by=self.inec_official
        )
        
        # Create candidates
        self.candidate1 = Candidate.objects.create(
            name='Candidate 1',
            party='Party A',
            position='President',
            election=self.election
        )
        
        self.candidate2 = Candidate.objects.create(
            name='Candidate 2',
            party='Party B',
            position='President',
            election=self.election
        )
        
        # Create ballot
        self.ballot = Ballot.objects.create(election=self.election)
        BallotCandidate.objects.create(
            ballot=self.ballot,
            candidate=self.candidate1,
            order=1
        )
        BallotCandidate.objects.create(
            ballot=self.ballot,
            candidate=self.candidate2,
            order=2
        )
    
    def test_cast_vote_success(self):
        """Test successful vote casting"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.voter_token.key)
        
        data = {
            'election_id': str(self.election.election_id),
            'candidate_id': str(self.candidate1.candidate_id)
        }
        
        response = self.client.post('/api/voting/cast-vote/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('vote_id', response.data)
        
        # Verify vote was created
        self.assertTrue(Vote.objects.filter(
            voter=self.voter,
            election=self.election,
            candidate=self.candidate1
        ).exists())
    
    def test_get_ballot(self):
        """Test getting ballot for election"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.voter_token.key)
        
        response = self.client.get(f'/api/voting/ballot/{self.election.election_id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('candidates', response.data)
        self.assertEqual(len(response.data['candidates']), 2)
    
    def test_voting_history(self):
        """Test getting voting history"""
        # Create a vote first
        Vote.objects.create(
            voter=self.voter,
            election=self.election,
            candidate=self.candidate1
        )
        
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.voter_token.key)
        
        response = self.client.get('/api/voting/history/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_start_voting_session(self):
        """Test starting a voting session"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.voter_token.key)
        
        data = {
            'election_id': str(self.election.election_id)
        }
        
        response = self.client.post('/api/voting/session/start/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('session_id', response.data)
        
        # Verify session was created
        self.assertTrue(VotingSession.objects.filter(
            voter=self.voter,
            election=self.election
        ).exists())
    
    def test_cast_vote_unauthorized(self):
        """Test vote casting without authentication"""
        data = {
            'election_id': str(self.election.election_id),
            'candidate_id': str(self.candidate1.candidate_id)
        }
        
        response = self.client.post('/api/voting/cast-vote/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_cast_vote_duplicate(self):
        """Test casting vote twice in same election"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.voter_token.key)
        
        # Cast first vote
        data = {
            'election_id': str(self.election.election_id),
            'candidate_id': str(self.candidate1.candidate_id)
        }
        self.client.post('/api/voting/cast-vote/', data, format='json')
        
        # Try to cast second vote
        data['candidate_id'] = str(self.candidate2.candidate_id)
        response = self.client.post('/api/voting/cast-vote/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
