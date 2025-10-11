from typing import Type

from rest_framework import status, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Election, Candidate
from .serializers import (
    ElectionSerializer, ElectionCreateSerializer, 
    CandidateSerializer, CandidateCreateSerializer,
    ElectionResultsSerializer
)


class ElectionViewSet(viewsets.ModelViewSet):
    queryset = Election._default_manager.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update']:
            return ElectionCreateSerializer
        return ElectionSerializer
    
    def get_permissions(self):
        # Only admins can create/update elections
        if self.action in ['create', 'update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        # Check if user is admin or superuser
        user = request.user
        if not (user.is_superuser or hasattr(user, 'admin') or user.role == 'admin'):
            return Response({
                'error': 'Only admins can create elections'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate._default_manager.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update']:
            return CandidateCreateSerializer
        return CandidateSerializer
    
    def get_permissions(self):
        # Only admins can create/update candidates
        if self.action in ['create', 'update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        # Check if user is admin or superuser
        user = request.user
        if not (user.is_superuser or hasattr(user, 'admin') or user.role == 'admin'):
            return Response({
                'error': 'Only admins can create candidates'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def election_results(request, election_id):
    """Get election results"""
    election = get_object_or_404(Election, election_id=election_id)
    
    if election.status != 'completed':
        return Response({
            'error': 'Election results are only available for completed elections'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = ElectionResultsSerializer(election)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def live_election_results(request, election_id):
    """Get live election results for transparency"""
    election = get_object_or_404(Election, election_id=election_id)
    
    # Only allow live results for ongoing elections
    if election.status != 'ongoing':
        return Response({
            'error': 'Live results are only available for ongoing elections'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get live results
    live_results = election.get_live_results()
    
    return Response({
        'election_id': election.election_id,
        'election_title': election.title,
        'election_type': election.type,
        'status': election.status,
        'live_results': live_results,
        'total_votes': sum(candidate['vote_count'] for candidate in live_results),
        'last_updated': timezone.now()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def active_elections(request):
    """Get currently active elections"""
    # Ensure statuses are up-to-date based on current time
    all_elections = Election._default_manager.all()
    for election in all_elections:
        try:
            election.check_and_update_status()
        except Exception:
            # Guard against unexpected errors in status update
            continue

    elections = Election._default_manager.filter(status='ongoing')
    serializer = ElectionSerializer(elections, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_election(request, election_id):
    """Start an election (Admin only)"""
    user = request.user
    if not (user.is_superuser or hasattr(user, 'admin') or user.role == 'admin'):
        return Response({
            'error': 'Only admins can start elections'
        }, status=status.HTTP_403_FORBIDDEN)
    
    election = get_object_or_404(Election, election_id=election_id)
    
    if election.start_election():
        return Response({
            'message': f'Election {election.title} started successfully',
            'election': ElectionSerializer(election).data
        })
    else:
        return Response({
            'error': 'Election cannot be started at this time'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def end_election(request, election_id):
    """End an election (Admin only)"""
    user = request.user
    if not (user.is_superuser or hasattr(user, 'admin') or user.role == 'admin'):
        return Response({
            'error': 'Only admins can end elections'
        }, status=status.HTTP_403_FORBIDDEN)
    
    election = get_object_or_404(Election, election_id=election_id)
    
    if election.end_election():
        return Response({
            'message': f'Election {election.title} ended successfully',
            'election': ElectionSerializer(election).data
        })
    else:
        return Response({
            'error': 'Election cannot be ended at this time'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_election_status(request):
    """Check and update all election statuses (Admin only)"""
    user = request.user
    if not (user.is_superuser or hasattr(user, 'admin') or user.role == 'admin'):
        return Response({
            'error': 'Only admins can check election statuses'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Import and run the management command
    from elections.management.commands.check_election_status import Command as CheckStatusCommand
    
    check_command = CheckStatusCommand()
    
    # Capture output
    import io
    from django.core.management import call_command
    from contextlib import redirect_stdout
    
    output = io.StringIO()
    
    try:
        with redirect_stdout(output):
            call_command('check_election_status')
        
        result = output.getvalue()
        
        return Response({
            'message': 'Election status check completed successfully',
            'result': result
        })
    except Exception as e:
        return Response({
            'error': f'Failed to check election statuses: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
