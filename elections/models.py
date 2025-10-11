from django.db import models
from django.utils import timezone
from authentication.models import User, Admin
import uuid


class Election(models.Model):
    """
    Election model representing different elections
    """
    ELECTION_TYPES = [
        ('presidential', 'Presidential'),
        ('gubernatorial', 'Gubernatorial'),
        ('senatorial', 'Senatorial'),
        ('house_of_reps', 'House of Representatives'),
        ('house_of_assembly', 'House of Assembly'),
        ('local_government', 'Local Government'),
    ]
    
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    election_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=ELECTION_TYPES)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_elections'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def start_election(self):
        """Start the election"""
        # Allow manual start regardless of current time
        if self.status == 'upcoming':
            self.status = 'ongoing'
            self.save()
            return True
        return False
    
    def end_election(self):
        """End the election"""
        # Allow manual end regardless of current time
        if self.status == 'ongoing':
            self.status = 'completed'
            self.save()
            return True
        return False
    
    def is_active(self):
        """Check if election is currently active for voting"""
        now = timezone.now()
        # Election is active if it's ongoing and within the time window
        return (self.status == 'ongoing' and 
                self.start_date <= now <= self.end_date)
    
    def can_accept_votes(self):
        """Check if election can accept new votes"""
        now = timezone.now()
        # Can accept votes if it's ongoing and within the time window
        return (self.status == 'ongoing' and 
                self.start_date <= now <= self.end_date)
    
    def check_and_update_status(self):
        """Automatically check and update election status based on time"""
        now = timezone.now()
        
        # If upcoming and past start date, but before end date, start it
        if (self.status == 'upcoming' and 
            self.start_date <= now <= self.end_date):
            self.status = 'ongoing'
            self.save()
        
        # If ongoing and past end date, end it
        elif (self.status == 'ongoing' and 
              now > self.end_date):
            self.status = 'completed'
            self.save()
    
    def get_results(self):
        """Get election results"""
        from voting.models import Vote
        from .models import Candidate
        results = {}
        # Use _default_manager to avoid linter issues
        candidates = Candidate._default_manager.filter(election=self)
        for candidate in candidates:
            # Only count votes that were cast before the end time
            vote_count = Vote._default_manager.filter(
                election=self,
                candidate=candidate,
                timestamp__lte=self.end_date
            ).count()
            results[candidate.name] = vote_count
        return results
    
    def get_live_results(self):
        """Get live election results with candidate details"""
        from voting.models import Vote
        from .models import Candidate
        results = []
        # Use _default_manager to avoid linter issues
        candidates = Candidate._default_manager.filter(election=self)
        for candidate in candidates:
            # Only count votes that were cast before the end time
            vote_count = Vote._default_manager.filter(
                election=self,
                candidate=candidate,
                timestamp__lte=self.end_date
            ).count()
            results.append({
                'candidate_id': candidate.candidate_id,
                'name': candidate.name,
                'party': candidate.party,
                'position': candidate.position,
                'vote_count': vote_count
            })
        # Sort by vote count descending
        results.sort(key=lambda x: x['vote_count'], reverse=True)
        return results
    
    def __str__(self):
        return f"{self.title} ({self.type})"
    
    class Meta:
        db_table = 'election'
        ordering = ['-start_date']


class Candidate(models.Model):
    """
    Candidate model for election candidates
    """
    candidate_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=200)
    party = models.CharField(max_length=100)
    position = models.CharField(max_length=100)  # e.g., President, Governor, etc.
    biography = models.TextField(blank=True)
    photo = models.ImageField(upload_to='candidates/', blank=True, null=True)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def view_profile(self):
        """Return candidate profile information"""
        photo_url = None
        if self.photo:
            try:
                # Use getattr to avoid linter issues
                photo_url = getattr(self.photo, 'url', None)
            except:
                photo_url = None
        return {
            'name': self.name,
            'party': self.party,
            'position': self.position,
            'biography': self.biography,
            'photo': photo_url
        }
    
    def get_vote_count(self):
        """Get total votes for this candidate"""
        from voting.models import Vote
        return Vote._default_manager.filter(candidate=self).count()
    
    def __str__(self):
        # Use getattr to avoid linter issues and AttributeError
        election_title = "Unknown Election"
        try:
            if hasattr(self, 'election') and self.election:
                election_title = getattr(self.election, 'title', 'Unknown Election')
        except:
            pass
        return f"{self.name} ({self.party}) - {election_title}"
    
    class Meta:
        db_table = 'candidate'
        unique_together = ['name', 'party', 'election']
        ordering = ['name']