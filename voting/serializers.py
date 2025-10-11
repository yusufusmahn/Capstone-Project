from rest_framework import serializers
from .models import Vote, VotingSession, Ballot, BallotCandidate
from elections.models import Election, Candidate
from elections.serializers import CandidateSerializer
from authentication.models import Voter


class VoteSerializer(serializers.ModelSerializer):
    voter_name = serializers.SerializerMethodField()
    election_title = serializers.SerializerMethodField()
    candidate_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Vote
        fields = ['vote_id', 'voter_name', 'election_title', 'candidate_name', 'timestamp', 'is_verified']
        read_only_fields = ['vote_id', 'voter_name', 'election_title', 'candidate_name', 'timestamp', 'is_verified']
    
    def get_voter_name(self, obj):
        return obj.voter.user.name
    
    def get_election_title(self, obj):
        return obj.election.title
    
    def get_candidate_name(self, obj):
        return obj.candidate.name


class CastVoteSerializer(serializers.Serializer):
    election_id = serializers.UUIDField()
    candidate_id = serializers.UUIDField()
    
    def validate_election_id(self, value):
        try:
            election = Election._default_manager.get(election_id=value)
            # Use the new method to check if election can accept votes
            if not election.can_accept_votes():
                raise serializers.ValidationError("Election is not currently accepting votes.")
            return value
        except Exception:
            raise serializers.ValidationError("Election not found.")
    
    def validate_candidate_id(self, value):
        try:
            candidate = Candidate._default_manager.get(candidate_id=value)
            return value
        except Exception:
            raise serializers.ValidationError("Candidate not found.")
    
    def validate(self, attrs):
        data = attrs.copy()
        try:
            election = Election._default_manager.get(election_id=data['election_id'])
            candidate = Candidate._default_manager.get(candidate_id=data['candidate_id'])
            
            # Check if candidate belongs to the election
            if candidate.election != election:
                raise serializers.ValidationError("Candidate does not belong to this election.")
            
            # Check if voter has already voted
            voter = self.context['request'].user.voter
            if Vote._default_manager.filter(voter=voter, election=election).exists():
                # Raise an explicit validation error so the client receives a clear message
                raise serializers.ValidationError("You have already voted in this election.")
            
            data['election'] = election
            data['candidate'] = candidate
            data['voter'] = voter
        except serializers.ValidationError:
            # Re-raise serializer validation errors so they are not masked
            raise
        except AttributeError:
            raise serializers.ValidationError("User is not a registered voter.")
        except Exception as e:
            # Preserve underlying exception details where possible for debugging
            raise serializers.ValidationError(str(e) or "Invalid election or candidate.")
        
        return data


class VotingSessionSerializer(serializers.ModelSerializer):
    voter_name = serializers.SerializerMethodField()
    election_title = serializers.SerializerMethodField()
    
    class Meta:
        model = VotingSession
        fields = ['session_id', 'voter_name', 'election_title', 'status', 'started_at', 'completed_at']
        read_only_fields = ['session_id', 'voter_name', 'election_title', 'started_at', 'completed_at']
    
    def get_voter_name(self, obj):
        return obj.voter.user.name
    
    def get_election_title(self, obj):
        return obj.election.title


class BallotCandidateSerializer(serializers.ModelSerializer):
    candidate = CandidateSerializer(read_only=True)
    
    class Meta:
        model = BallotCandidate
        fields = ['candidate', 'order']


class BallotSerializer(serializers.ModelSerializer):
    candidates = serializers.SerializerMethodField()
    election_title = serializers.SerializerMethodField()
    
    class Meta:
        model = Ballot
        fields = ['ballot_id', 'election_title', 'candidates', 'created_at']
        read_only_fields = ['ballot_id', 'election_title', 'created_at']
    
    def get_candidates(self, obj):
        ballot_candidates = obj.get_candidate_list()
        return BallotCandidateSerializer(ballot_candidates, many=True).data
    
    def get_election_title(self, obj):
        return obj.election.title


class VoteVerificationSerializer(serializers.Serializer):
    vote_id = serializers.UUIDField()
    verification_code = serializers.CharField(max_length=50, required=False)
    
    def validate_vote_id(self, value):
        try:
            vote = Vote._default_manager.get(vote_id=value)
            return value
        except Exception:
            raise serializers.ValidationError("Vote not found.")


class VotingStatsSerializer(serializers.Serializer):
    total_votes_cast = serializers.IntegerField()
    total_eligible_voters = serializers.IntegerField()
    voter_turnout_percentage = serializers.FloatField()
    votes_by_election = serializers.DictField()
    voting_sessions_active = serializers.IntegerField()
    
    def to_representation(self, instance):
        # Handle case where instance is None
        if instance is None:
            instance = {}
            
        # Calculate voting statistics
        total_votes = Vote._default_manager.count()
        total_voters = Voter._default_manager.filter(can_vote=True).count()
        turnout = (total_votes / total_voters * 100) if total_voters > 0 else 0
        
        # Votes by election
        from django.db.models import Count
        votes_queryset = Vote._default_manager.values('election__title').annotate(count=Count('id'))
        votes_by_election = dict(votes_queryset.values_list('election__title', 'count'))
        
        # Active voting sessions
        active_sessions = VotingSession._default_manager.filter(
            status__in=['started', 'in_progress']
        ).count()
        
        return {
            'total_votes_cast': total_votes,
            'total_eligible_voters': total_voters,
            'voter_turnout_percentage': round(turnout, 2),
            'votes_by_election': votes_by_election if votes_by_election else {},
            'voting_sessions_active': active_sessions or 0
        }