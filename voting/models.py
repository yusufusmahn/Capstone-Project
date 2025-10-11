from django.db import models
from django.utils import timezone
from cryptography.fernet import Fernet
from django.conf import settings
from authentication.models import Voter
from elections.models import Election, Candidate
import uuid
import json


class Vote(models.Model):
    """
    Vote model for storing encrypted votes
    """
    vote_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE, related_name='votes')
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='votes')
    encrypted_vote_data = models.TextField()  # Encrypted vote information
    timestamp = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    def record_vote(self, vote_data):
        """Encrypt and record vote data"""
        # Encrypt the vote data
        cipher_suite = Fernet(settings.VOTE_ENCRYPTION_KEY.encode()[:44] + b'=' * 4)
        encrypted_data = cipher_suite.encrypt(json.dumps(vote_data).encode())
        self.encrypted_vote_data = encrypted_data.decode()
        self.save()
        return True
    
    def verify_vote(self):
        """Verify the vote (for auditing purposes)"""
        try:
            cipher_suite = Fernet(settings.VOTE_ENCRYPTION_KEY.encode()[:44] + b'=' * 4)
            decrypted_data = cipher_suite.decrypt(self.encrypted_vote_data.encode())
            vote_data = json.loads(decrypted_data.decode())
            
            # Verify vote integrity
            if (vote_data.get('voter_id') == str(self.voter.voter_id) and
                vote_data.get('election_id') == str(self.election.election_id) and
                vote_data.get('candidate_id') == str(self.candidate.candidate_id)):
                self.is_verified = True
                self.save()
                return True
        except Exception as e:
            print(f"Vote verification failed: {e}")
        
        return False
    
    def __str__(self):
        return f"Vote by {self.voter.user.name} in {self.election.title}"
    
    class Meta:
        db_table = 'vote'
        unique_together = ['voter', 'election']  # One vote per voter per election
        ordering = ['-timestamp']


class VotingSession(models.Model):
    """
    Voting session to track voter's voting process
    """
    SESSION_STATUS = [
        ('started', 'Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
        ('error', 'Error'),
    ]
    
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE, related_name='voting_sessions')
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='started')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    def complete_session(self):
        """Mark session as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def abandon_session(self):
        """Mark session as abandoned"""
        self.status = 'abandoned'
        self.save()
    
    def __str__(self):
        return f"Voting session for {self.voter.user.name} - {self.election.title}"
    
    class Meta:
        db_table = 'voting_session'
        ordering = ['-started_at']


class Ballot(models.Model):
    """
    Ballot model for organizing candidates in elections
    """
    ballot_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    election = models.OneToOneField(Election, on_delete=models.CASCADE, related_name='ballot')
    candidates = models.ManyToManyField(Candidate, through='BallotCandidate')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_candidate_list(self):
        """Get ordered list of candidates on this ballot"""
        return self.ballotcandidate_set.order_by('order').select_related('candidate')
    
    def __str__(self):
        return f"Ballot for {self.election.title}"
    
    class Meta:
        db_table = 'ballot'


class BallotCandidate(models.Model):
    """
    Through model for Ballot and Candidate relationship with ordering
    """
    ballot = models.ForeignKey(Ballot, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()  # Order of appearance on ballot
    
    class Meta:
        db_table = 'ballot_candidate'
        unique_together = ['ballot', 'candidate']
        ordering = ['order']
