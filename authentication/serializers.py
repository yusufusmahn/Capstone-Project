from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from datetime import date
from .models import User, Voter, Admin, InecOfficial, validate_age, validate_voter_id


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'user_id', 'name', 'phone_number', 'email', 'dob', 'role', 'status', 'created_at']
        read_only_fields = ['id', 'user_id', 'created_at']


class VoterSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Voter
        fields = ['user', 'voter_id', 'voters_card_id', 'registration_verified', 'can_vote']
        read_only_fields = ['registration_verified']


class AdminSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Admin
        fields = ['user', 'admin_id']


class InecOfficialSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = InecOfficial
        fields = ['user', 'official_id']


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')
        
        if phone_number and password:
            # Clean phone number
            phone_clean = phone_number.replace(' ', '').replace('-', '')
            
            user = authenticate(phone_number=phone_clean, password=password)
            if user:
                if user.is_active:
                    attrs['user'] = user
                else:
                    raise serializers.ValidationError('User account is disabled.')
            else:
                raise serializers.ValidationError('Invalid phone number or password.')
        else:
            raise serializers.ValidationError('Must include phone number and password.')
        
        return attrs


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    voter_id = serializers.CharField(
        required=True, 
        max_length=10,
        help_text="10-character alphanumeric voter ID"
    )
    voters_card_id = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['name', 'phone_number', 'dob', 'password', 'password_confirm', 'voter_id', 'voters_card_id']
    
    def validate_phone_number(self, value):
        """Validate phone number format and uniqueness"""
        # Remove spaces and normalize format - simple validation for now
        phone_clean = str(value).replace(' ', '').replace('-', '')
        
        # Check if phone number already exists
        if User._default_manager.filter(phone_number=phone_clean).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        
        return phone_clean
    
    def validate_dob(self, value):
        """Validate date of birth - user must be at least 18 years old"""
        if not value:
            raise serializers.ValidationError("Date of birth is required.")
        
        try:
            validate_age(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
        
        return value
    
    def validate_voter_id(self, value):
        """Validate voter ID format and uniqueness"""
        if not value:
            raise serializers.ValidationError("Voter ID is required.")
        
        try:
            validated_id = validate_voter_id(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
        
        # Check uniqueness
        if Voter._default_manager.filter(voter_id=validated_id).exists():
            raise serializers.ValidationError("A voter with this ID already exists.")
        
        return validated_id
    
    def validate_voters_card_id(self, value):
        """Validate voter's card ID uniqueness if provided"""
        if value and Voter._default_manager.filter(voters_card_id=value).exists():
            raise serializers.ValidationError("A voter with this card ID already exists.")
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        voter_id = validated_data.pop('voter_id')
        voters_card_id = validated_data.pop('voters_card_id', None)
        
        # Normalize phone number
        phone_number = validated_data['phone_number']
        validated_data['phone_number'] = phone_number.replace(' ', '').replace('-', '')
        
        # Set default role to voter
        validated_data['role'] = 'voter'
        
        user = User._default_manager.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # Create voter profile with provided voter_id
        Voter._default_manager.create(
            user=user,
            voter_id=voter_id,
            voters_card_id=voters_card_id if voters_card_id else None
        )
        
        return user


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New password and confirm password do not match.")
        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError("New password must be different from current password.")
        return attrs
    
    def save(self, **kwargs):
        user = self.context['request'].user
        validated_data = getattr(self, 'validated_data', {})
        if validated_data and 'new_password' in validated_data:
            user.set_password(validated_data['new_password'])
        user.save()
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    
    def validate_phone_number(self, value):
        """Validate phone number exists in the system"""
        # Clean phone number
        phone_clean = str(value).replace(' ', '').replace('-', '')
        
        # Check if phone number exists
        if not User._default_manager.filter(phone_number=phone_clean).exists():
            raise serializers.ValidationError("No account found with this phone number.")
        
        return phone_clean


class PasswordResetSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def save(self, **kwargs):
        validated_data = getattr(self, 'validated_data', {})
        if not validated_data or 'phone_number' not in validated_data:
            raise serializers.ValidationError("Phone number is required.")
            
        phone_number = validated_data['phone_number']
        # Clean phone number
        phone_clean = str(phone_number).replace(' ', '').replace('-', '')
        
        try:
            user = User._default_manager.get(phone_number=phone_clean)
            if validated_data and 'new_password' in validated_data:
                user.set_password(validated_data['new_password'])
            user.save()
            return user
        except User._default_manager.model.DoesNotExist:
            raise serializers.ValidationError("User not found.")