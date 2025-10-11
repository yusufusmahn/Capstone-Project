from django.db import models
from django.utils import timezone
from authentication.models import User, Voter, InecOfficial
import uuid


class IncidentReport(models.Model):
    """
    Incident report model for reporting voting irregularities
    """
    INCIDENT_TYPES = [
        ('voter_intimidation', 'Voter Intimidation'),
        ('ballot_stuffing', 'Ballot Stuffing'),
        ('technical_issue', 'Technical Issue'),
        ('violence', 'Violence'),
        ('bribery', 'Bribery'),
        ('equipment_malfunction', 'Equipment Malfunction'),
        ('unauthorized_access', 'Unauthorized Access'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    report_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incident_reports')
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE, null=True, blank=True, related_name='incidents')
    incident_type = models.CharField(max_length=30, choices=INCIDENT_TYPES)
    description = models.TextField()
    location = models.CharField(max_length=500, blank=True)  # GPS coordinates or address
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_to = models.ForeignKey(InecOfficial, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_incidents')
    resolution_notes = models.TextField(blank=True)
    
    def submit_report(self):
        """Submit the incident report"""
        self.status = 'pending'
        self.save()
        return True
    
    def verify_report(self):
        """Verify the incident report"""
        self.status = 'under_review'
        self.save()
        return True
    
    def assign_to_official(self, official):
        """Assign incident to an INEC official"""
        self.assigned_to = official
        self.status = 'investigating'
        self.save()
    
    def resolve_incident(self, resolution_notes):
        """Resolve the incident"""
        self.status = 'resolved'
        self.resolution_notes = resolution_notes
        self.updated_at = timezone.now()
        self.save()
    
    def dismiss_incident(self, reason):
        """Dismiss the incident"""
        self.status = 'dismissed'
        self.resolution_notes = reason
        self.updated_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Incident {self.report_id}: {self.incident_type} by {self.reporter.name}"
    
    class Meta:
        db_table = 'incident_report'
        ordering = ['-created_at']


class IncidentEvidence(models.Model):
    """
    Evidence attached to incident reports
    """
    EVIDENCE_TYPES = [
        ('photo', 'Photo'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
    ]
    
    evidence_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE, related_name='evidence')
    evidence_type = models.CharField(max_length=10, choices=EVIDENCE_TYPES)
    file = models.FileField(upload_to='incident_evidence/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # in bytes
    file_hash = models.CharField(max_length=64, blank=True)  # SHA-256 hash for integrity
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            # File hash calculation removed for simplicity
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Evidence for {self.incident.report_id}: {self.evidence_type}"
    
    class Meta:
        db_table = 'incident_evidence'
        ordering = ['-uploaded_at']


class IncidentResponse(models.Model):
    """
    Response/action taken on incident reports
    """
    ACTION_TYPES = [
        ('investigation_started', 'Investigation Started'),
        ('evidence_collected', 'Evidence Collected'),
        ('witness_interviewed', 'Witness Interviewed'),
        ('corrective_action', 'Corrective Action Taken'),
        ('case_closed', 'Case Closed'),
        ('escalated', 'Escalated to Higher Authority'),
    ]
    
    response_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE, related_name='responses')
    responder = models.ForeignKey(InecOfficial, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Response to {self.incident.report_id}: {self.action_type}"
    
    class Meta:
        db_table = 'incident_response'
        ordering = ['-created_at']
