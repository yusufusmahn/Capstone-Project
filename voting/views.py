from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Vote, VotingSession, Ballot
from .serializers import (
    VoteSerializer, CastVoteSerializer, VotingSessionSerializer,
    BallotSerializer, VoteVerificationSerializer, VotingStatsSerializer
)
from elections.models import Election, Candidate
from authentication.models import Voter


class CastVoteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Check if user is a voter
        if not hasattr(request.user, 'voter'):
            return Response({
                'error': 'Only registered voters can cast votes'
            }, status=status.HTTP_403_FORBIDDEN)
        
        voter = request.user.voter
        
        # Check if voter is eligible
        if not voter.can_vote or not voter.registration_verified:
            return Response({
                'error': 'You are not eligible to vote'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = CastVoteSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Check if validated_data exists
            if serializer.validated_data is None:
                return Response({
                    'error': 'Invalid data validation'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Access the validated data with explicit None checks
            validated_data = serializer.validated_data
            election = validated_data.get('election') if validated_data is not None else None
            candidate = validated_data.get('candidate') if validated_data is not None else None
            
            if not election or not candidate:
                return Response({
                    'error': 'Invalid election or candidate data'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create vote record with encryption
            vote = Vote._default_manager.create(
                voter=voter,
                election=election,
                candidate=candidate
            )
            
            # Encrypt vote data
            vote_data = {
                'voter_id': str(voter.voter_id),
                'election_id': str(election.election_id),
                'candidate_id': str(candidate.candidate_id),
                'timestamp': vote.timestamp.isoformat()
            }
            vote.record_vote(vote_data)
            
            return Response({
                'message': 'Vote cast successfully',
                'vote_id': vote.vote_id,
                'vote': VoteSerializer(vote).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_ballot(request, election_id):
    """Get ballot for an election"""
    election = get_object_or_404(Election, election_id=election_id)
    
    if not election.is_active():
        return Response({
            'error': 'Election is not currently active'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ballot = election.ballot
        serializer = BallotSerializer(ballot)
        return Response(serializer.data)
    except Exception:
        # Create ballot if it doesn't exist
        ballot = Ballot._default_manager.create(election=election)
        # Add all candidates to ballot
        for i, candidate in enumerate(election.candidates.all(), 1):
            ballot.ballotcandidate_set.create(candidate=candidate, order=i)
        
        serializer = BallotSerializer(ballot)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def voting_history(request):
    """Get voting history for current user"""
    if not hasattr(request.user, 'voter'):
        return Response({
            'error': 'Only voters can view voting history'
        }, status=status.HTTP_403_FORBIDDEN)
    
    votes = Vote._default_manager.filter(voter=request.user.voter)
    serializer = VoteSerializer(votes, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_vote(request):
    """Verify a vote"""
    serializer = VoteVerificationSerializer(data=request.data)
    if serializer.is_valid():
        # Check if validated_data exists
        if serializer.validated_data is None:
            return Response({
                'error': 'Invalid data validation'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Access the validated data with explicit None checks
        validated_data = serializer.validated_data
        vote_id = validated_data.get('vote_id') if validated_data is not None else None
        
        if not vote_id:
            return Response({
                'error': 'Vote ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vote = Vote._default_manager.get(vote_id=vote_id)
            
            # Only allow voter to verify their own vote
            if hasattr(request.user, 'voter') and vote.voter == request.user.voter:
                is_verified = vote.verify_vote()
                return Response({
                    'verified': is_verified,
                    'message': 'Vote verification successful' if is_verified else 'Vote verification failed'
                })
            else:
                return Response({
                    'error': 'You can only verify your own votes'
                }, status=status.HTTP_403_FORBIDDEN)
                
        except Exception:
            return Response({
                'error': 'Vote not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_voting_session(request):
    """Start a voting session"""
    if not hasattr(request.user, 'voter'):
        return Response({
            'error': 'Only voters can start voting sessions'
        }, status=status.HTTP_403_FORBIDDEN)
    
    election_id = request.data.get('election_id')
    if not election_id:
        return Response({
            'error': 'Election ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    election = get_object_or_404(Election, election_id=election_id)
    
    # Create voting session
    session = VotingSession._default_manager.create(
        voter=request.user.voter,
        election=election,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    serializer = VotingSessionSerializer(session)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def voting_stats(request):
    """Get voting statistics (Admin/INEC only)"""
    if not (hasattr(request.user, 'admin') or hasattr(request.user, 'inecofficial')):
        return Response({
            'error': 'Admin or INEC Official access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = VotingStatsSerializer({})
    return Response(serializer.data)