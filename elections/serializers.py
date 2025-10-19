from rest_framework import serializers
from .models import Election, Candidate
from authentication.serializers import UserSerializer
from voting.models import Vote
from authentication.models import Voter

class CandidateSerializer(serializers.ModelSerializer):
    vote_count = serializers.SerializerMethodField()
    # Return an absolute URL for the photo when possible
    photo = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidate
        fields = ['candidate_id', 'name', 'party', 'position', 'biography', 'photo', 'election', 'vote_count', 'created_at']
        read_only_fields = ['candidate_id', 'vote_count', 'created_at']
    
    def get_vote_count(self, obj):
        return obj.get_vote_count()

    def get_photo(self, obj):
        # Try to return an absolute URL using request context if available
        photo_url = None
        if obj.photo:
            try:
                photo_url = getattr(obj.photo, 'url', None)
            except Exception:
                photo_url = None

        request = self.context.get('request') if hasattr(self, 'context') else None
        if photo_url:
            if request is not None:
                try:
                    return request.build_absolute_uri(photo_url)
                except Exception:
                    return photo_url
            return photo_url

        return None


class ElectionSerializer(serializers.ModelSerializer):
    candidates = CandidateSerializer(many=True, read_only=True)
    results = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    created_by = UserSerializer(read_only=True)
    vote_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Election
        fields = [
            'id',
            'election_id', 'title', 'type', 'description', 'start_date', 'end_date', 
            'status', 'created_by', 'candidates', 'results', 'is_active', 'created_at', 'vote_count'
        ]
        read_only_fields = ['election_id', 'results', 'is_active', 'created_at', 'vote_count']
    
    def get_results(self, obj):
        if obj.status == 'completed':
            return obj.get_results()
        return None
    
    def get_is_active(self, obj):
        return obj.is_active()
        
    def get_vote_count(self, obj):
        # Count all votes for this election
        return Vote._default_manager.filter(election=obj).count()


class ElectionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Election
        fields = ['title', 'type', 'description', 'start_date', 'end_date']
    
    def create(self, validated_data):
        # Set created_by to current user (only Admin or Super Admin)
        user = self.context['request'].user
        # Only allow admins to create elections
        if hasattr(user, 'admin'):
            validated_data['created_by'] = user
        else:
            # This shouldn't happen with proper permissions, but just in case
            validated_data['created_by'] = user
        return super().create(validated_data)


class CandidateCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ['name', 'party', 'position', 'biography', 'photo', 'election']

    # Allow election to be specified by its election_id (UUID string)
    election = serializers.SlugRelatedField(
        queryset=Election._default_manager.all(),
        slug_field='election_id'
    )


class ElectionResultsSerializer(serializers.Serializer):
    election = ElectionSerializer(read_only=True)
    total_votes = serializers.IntegerField()
    results = serializers.DictField()
    voter_turnout = serializers.FloatField()
    
    def to_representation(self, instance):
        election = instance
        results = election.get_results()
        total_votes = sum(results.values()) if results else 0
        
        # Calculate voter turnout (assuming we have total registered voters)
        from authentication.models import Voter
        total_voters = Voter._default_manager.filter(can_vote=True).count()
        voter_turnout = (total_votes / total_voters * 100) if total_voters > 0 else 0
        
        return {
            'election': ElectionSerializer(election).data,
            'total_votes': total_votes,
            'results': results,
            'voter_turnout': round(voter_turnout, 2)
        }