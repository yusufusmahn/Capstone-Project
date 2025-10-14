from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import uuid
import random
import string
from datetime import date


def validate_age(birth_date):
    """Validate that user is at least 18 years old"""
    today = timezone.now().date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    if age < 18:
        raise ValidationError("You must be at least 18 years old to register.")
    
    return birth_date


def validate_voter_id(voter_id):
    """Validate voter ID format - must be 10-character alphanumeric"""
    if not voter_id:
        raise ValidationError("Voter ID is required.")
    
    if len(voter_id) != 10:
        raise ValidationError("Voter ID must be exactly 10 characters long.")
    
    if not voter_id.isalnum():
        raise ValidationError("Voter ID must contain only letters and numbers.")
    
    return voter_id.upper()  # Convert to uppercase for consistency


# Simple phone regex for testing
phone_regex = RegexValidator(
    regex=r'^[0-9+\-\s]+$',
    message="Phone number can contain digits, +, -, and spaces."
)


class Role(models.TextChoices):
    VOTER = 'voter', 'Voter'
    ADMIN = 'admin', 'Admin'
    INEC_OFFICIAL = 'inec_official', 'INEC Official'
    OBSERVER = 'observer', 'Observer/Security'


class UserManager(BaseUserManager):
    """
    Custom user manager for phone number authentication
    """
    def create_user(self, phone_number, name, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('Phone number is required')
        if not name:
            raise ValueError('Name is required')
        
        # Validate age if dob is provided
        if 'dob' in extra_fields and extra_fields['dob']:
            validate_age(extra_fields['dob'])
        
        user = self.model(
            phone_number=phone_number,
            name=name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', Role.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(phone_number, name, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser
    """
    user_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    dob = models.DateField(null=True, blank=True, verbose_name="Date of Birth")
    phone_number = models.CharField(
        max_length=15, 
        unique=True,
        validators=[phone_regex],
        help_text="Phone number must be in format: '+999999999'. Up to 15 digits allowed."
    )
    status = models.BooleanField(default=True)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VOTER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Override username requirement
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['name']
    
    objects = UserManager()
    
    def clean(self):
        super().clean()
        if self.dob:
            validate_age(self.dob)
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.phone_number})"
    
    class Meta:
        db_table = 'auth_user'


class Voter(models.Model):
    """
    Voter profile extending User model
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    voter_id = models.CharField(
        max_length=10, 
        unique=True,
        help_text="10-character alphanumeric voter ID provided by voter"
    )
    voters_card_id = models.CharField(max_length=20, unique=True, null=True, blank=True)  # VIN - Voter Identification Number
    registration_verified = models.BooleanField(default=False)
    # Default to False so voters are not eligible to vote until approved
    can_vote = models.BooleanField(default=False)
    
    def clean(self):
        super().clean()
        if self.voter_id:
            self.voter_id = validate_voter_id(self.voter_id)
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def register(self):
        """Register voter - to be implemented with INEC verification"""
        pass
    
    def cast_vote(self, election, candidate):
        """Cast vote for a candidate in an election"""
        from voting.models import Vote
        return Vote._default_manager.create(
            voter=self,
            election=election,
            candidate=candidate
        )
    
    def report_incident(self, description, location=None, media_evidence=None):
        """Report an incident"""
        from incidents.models import IncidentReport
        return IncidentReport._default_manager.create(
            reporter=self.user,
            voter=self,
            description=description,
            location=location,
            media_evidence=media_evidence
        )
    
    def __str__(self):
        return f"Voter: {self.user.name} ({self.voter_id})"
    
    class Meta:
        db_table = 'voter'


class Admin(models.Model):
    """
    Admin profile for administrative functions
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    admin_id = models.CharField(max_length=20, unique=True)
    
    def promote(self, user):
        """Promote user to admin or other role"""
        pass
    
    def demote(self, user):
        """Demote user from admin role"""
        pass
    
    def __str__(self):
        return f"Admin: {self.user.name} ({self.admin_id})"
    
    class Meta:
        db_table = 'admin'


class InecOfficial(models.Model):
    """
    INEC Official profile for election management
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    official_id = models.CharField(max_length=20, unique=True)
    
    def view_results(self, election):
        """View election results"""
        pass
    
    def count_votes(self, election):
        """Count votes for an election"""
        pass
    
    def respond_to_incident(self, incident):
        """Respond to an incident report"""
        pass
    
    def __str__(self):
        return f"INEC Official: {self.user.name} ({self.official_id})"
    
    class Meta:
        db_table = 'inec_official'