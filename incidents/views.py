from rest_framework import status, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import IncidentReport, IncidentEvidence, IncidentResponse
from .serializers import (
    IncidentReportSerializer, IncidentReportCreateSerializer,
    IncidentResponseCreateSerializer, IncidentAssignmentSerializer,
    IncidentStatusUpdateSerializer, IncidentStatsSerializer
)
from authentication.models import InecOfficial
from django.db import transaction


class IncidentReportViewSet(viewsets.ModelViewSet):
    queryset = IncidentReport._default_manager.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = IncidentReportSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return IncidentReportCreateSerializer
        return IncidentReportSerializer
    
    def get_queryset(self):
        queryset = IncidentReport._default_manager.all()
        
        # Filter based on user role
        if hasattr(self.request.user, 'voter'):
            # Voters can only see their own reports
            queryset = queryset.filter(reporter=self.request.user)
        elif hasattr(self.request.user, 'inecofficial'):
            # INEC officials should be able to view reports to pick them up
            # Show all reports (they can filter/assign as needed)
            queryset = queryset
        elif hasattr(self.request.user, 'admin') or self.request.user.is_superuser:
            # Admins and superusers can see all reports
            queryset = queryset
        
        return queryset


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def assign_incident(request):
    """Assign incident to INEC official (Admin only)"""
    # Admins can assign any incident. INEC officials may self-assign (pick up) incidents.
    is_admin = hasattr(request.user, 'admin') or request.user.is_superuser
    
    serializer = IncidentAssignmentSerializer(data=request.data)
    if serializer.is_valid():
        # Safely access validated_data
        validated_data = getattr(serializer, 'validated_data', {})
        if validated_data and isinstance(validated_data, dict):
            incident_id = validated_data.get('incident_id')
            official_id = validated_data.get('official_id')
        else:
            return Response({
                'error': 'Invalid data validation'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Use a transaction and lock the incident row to avoid race conditions
        try:
            with transaction.atomic():
                incident = IncidentReport._default_manager.select_for_update().get(report_id=incident_id)

                # If incident already assigned
                if incident.assigned_to:
                    # If assigned to the same official, it's idempotent
                    current_official_user_id = getattr(incident.assigned_to.user, 'user_id', None)
                    if str(current_official_user_id) == str(official_id):
                        # already assigned to requested official, return success
                        return Response({
                            'message': 'Incident already assigned to this official',
                            'incident': IncidentReportSerializer(incident).data
                        })

                    # If requester is not admin, they cannot reassign an already assigned incident
                    if not is_admin:
                        # Provide friendly context to the client so the UI can show who currently owns the incident
                        assigned_name = getattr(incident.assigned_to.user, 'name', None)
                        assigned_user_id = getattr(incident.assigned_to.user, 'user_id', None)
                        return Response({
                            'error': 'Incident already assigned to another official and cannot be reassigned',
                            'assigned_to_name': assigned_name,
                            'assigned_to_id': str(assigned_user_id) if assigned_user_id else None
                        }, status=status.HTTP_403_FORBIDDEN)

                # At this point either unassigned or requester is admin (allowed to assign/reassign)
                official = get_object_or_404(InecOfficial, user__user_id=official_id)
                incident.assign_to_official(official)

        except IncidentReport.DoesNotExist:
            return Response({'error': 'Incident not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'message': 'Incident assigned successfully',
            'incident': IncidentReportSerializer(incident).data
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_incident_status(request, incident_id):
    """Update incident status (INEC Official only)"""
    # Allow INEC officials, admins or superusers to update incident status
    if not (hasattr(request.user, 'inecofficial') or hasattr(request.user, 'admin') or request.user.is_superuser):
        return Response({
            'error': 'INEC Official or Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    incident = get_object_or_404(IncidentReport, report_id=incident_id)
    
    # If the user is an INEC official, enforce assignment restriction; admins/superusers may update any
    if hasattr(request.user, 'inecofficial'):
        if incident.assigned_to != request.user.inecofficial:
            return Response({
                'error': 'You can only update incidents assigned to you'
            }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = IncidentStatusUpdateSerializer(data=request.data)
    if serializer.is_valid():
        # Safely access validated_data
        validated_data = getattr(serializer, 'validated_data', {})
        if validated_data and isinstance(validated_data, dict):
            new_status = validated_data.get('status')
            resolution_notes = validated_data.get('resolution_notes', '')
        else:
            return Response({
                'error': 'Invalid data validation'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        incident.status = new_status
        if resolution_notes:
            incident.resolution_notes = resolution_notes
        incident.save()
        
        if new_status == 'resolved':
            incident.resolve_incident(resolution_notes)
        elif new_status == 'dismissed':
            incident.dismiss_incident(resolution_notes)
        
        return Response({
            'message': 'Incident status updated successfully',
            'incident': IncidentReportSerializer(incident).data
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_incident_response(request):
    """Add response to incident (INEC Official only)"""
    # Allow INEC officials, admins, or superusers to add responses
    if not (hasattr(request.user, 'inecofficial') or hasattr(request.user, 'admin') or request.user.is_superuser):
        return Response({
            'error': 'INEC Official or Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = IncidentResponseCreateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        response = serializer.save()
        # Check if response has response_id attribute
        response_id = getattr(response, 'response_id', None)
        return Response({
            'message': 'Response added successfully',
            'response_id': str(response_id) if response_id else 'Unknown'
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def incident_stats(request):
    """Get incident statistics (Admin/INEC only)"""
    if not (hasattr(request.user, 'admin') or hasattr(request.user, 'inecofficial')):
        return Response({
            'error': 'Admin or INEC Official access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = IncidentStatsSerializer({})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_incidents(request):
    """Get incidents reported by current user"""
    incidents = IncidentReport._default_manager.filter(reporter=request.user)
    serializer = IncidentReportSerializer(incidents, many=True)
    return Response(serializer.data)