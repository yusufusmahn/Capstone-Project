from rest_framework import serializers
from .models import IncidentReport, IncidentEvidence, IncidentResponse
from authentication.models import User, InecOfficial


class IncidentEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentEvidence
        fields = ['evidence_id', 'evidence_type', 'file', 'description', 'uploaded_at', 'file_size']
        read_only_fields = ['evidence_id', 'uploaded_at', 'file_size']


class IncidentResponseSerializer(serializers.ModelSerializer):
    responder_name = serializers.SerializerMethodField()
    
    class Meta:
        model = IncidentResponse
        fields = ['response_id', 'action_type', 'description', 'responder_name', 'created_at']
        read_only_fields = ['response_id', 'responder_name', 'created_at']
    
    def get_responder_name(self, obj):
        return obj.responder.user.name


class IncidentReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.SerializerMethodField()
    voter_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    evidence = IncidentEvidenceSerializer(many=True, read_only=True)
    responses = IncidentResponseSerializer(many=True, read_only=True)
    
    class Meta:
        model = IncidentReport
        fields = [
            'report_id', 'reporter_name', 'voter_name', 'incident_type', 'description', 
            'location', 'status', 'priority', 'created_at', 'updated_at', 
            'assigned_to_name', 'resolution_notes', 'evidence', 'responses'
        ]
        read_only_fields = [
            'report_id', 'reporter_name', 'voter_name', 'assigned_to_name', 
            'created_at', 'updated_at', 'evidence', 'responses'
        ]
    
    def get_reporter_name(self, obj):
        return obj.reporter.name
    
    def get_voter_name(self, obj):
        return obj.voter.user.name if obj.voter else None
    
    def get_assigned_to_name(self, obj):
        return obj.assigned_to.user.name if obj.assigned_to else None


class IncidentReportCreateSerializer(serializers.ModelSerializer):
    evidence_files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = IncidentReport
        fields = ['incident_type', 'description', 'location', 'priority', 'evidence_files']
    
    def create(self, validated_data):
        # For multipart/form-data, files may be provided in request.FILES rather than in validated_data
        evidence_files = validated_data.pop('evidence_files', [])
        if (not evidence_files) and self.context.get('request') is not None:
            try:
                request_files = self.context['request'].FILES.getlist('evidence_files')
                if request_files:
                    evidence_files = request_files
            except Exception:
                evidence_files = evidence_files
        validated_data['reporter'] = self.context['request'].user
        
        # If reporter is a voter, set voter field
        try:
            voter = self.context['request'].user.voter
            validated_data['voter'] = voter
        except AttributeError:
            pass  # Not a voter
        
        incident = super().create(validated_data)
        
        # Create evidence records
        for file in evidence_files:
            evidence_type = self._get_evidence_type(file.name)
            IncidentEvidence._default_manager.create(
                incident=incident,
                evidence_type=evidence_type,
                file=file,
                description=f"Evidence for incident {incident.report_id}"
            )
        
        return incident
    
    def _get_evidence_type(self, filename):
        """Determine evidence type based on file extension"""
        ext = filename.lower().split('.')[-1]
        if ext in ['jpg', 'jpeg', 'png', 'gif']:
            return 'photo'
        elif ext in ['mp4', 'avi', 'mov']:
            return 'video'
        elif ext in ['mp3', 'wav', 'aac']:
            return 'audio'
        else:
            return 'document'


class IncidentResponseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentResponse
        fields = ['incident', 'action_type', 'description']
    
    def create(self, validated_data):
        validated_data['responder'] = self.context['request'].user.inecofficial
        return super().create(validated_data)


class IncidentAssignmentSerializer(serializers.Serializer):
    incident_id = serializers.UUIDField()
    official_id = serializers.UUIDField()
    
    def validate_incident_id(self, value):
        try:
            incident = IncidentReport._default_manager.get(report_id=value)
            return value
        except Exception:
            raise serializers.ValidationError("Incident not found.")
    
    def validate_official_id(self, value):
        try:
            official = InecOfficial._default_manager.get(user__user_id=value)
            return value
        except Exception:
            raise serializers.ValidationError("INEC Official not found.")


class IncidentStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=IncidentReport.STATUS_CHOICES)
    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        if attrs['status'] in ['resolved', 'dismissed'] and not attrs.get('resolution_notes'):
            raise serializers.ValidationError("Resolution notes are required when resolving or dismissing an incident.")
        return attrs


class IncidentStatsSerializer(serializers.Serializer):
    total_incidents = serializers.IntegerField()
    incidents_by_status = serializers.DictField()
    incidents_by_type = serializers.DictField()
    incidents_by_priority = serializers.DictField()
    pending_incidents = serializers.IntegerField()
    resolved_incidents = serializers.IntegerField()
    
    def to_representation(self, instance):
        from django.db.models import Count
        
        total_incidents = IncidentReport._default_manager.count()
        
        # Group by status
        by_status = dict(
            IncidentReport._default_manager.values('status').annotate(
                count=Count('id')
            ).values_list('status', 'count')
        )
        
        # Group by type
        by_type = dict(
            IncidentReport._default_manager.values('incident_type').annotate(
                count=Count('id')
            ).values_list('incident_type', 'count')
        )
        
        # Group by priority
        by_priority = dict(
            IncidentReport._default_manager.values('priority').annotate(
                count=Count('id')
            ).values_list('priority', 'count')
        )
        
        pending_count = IncidentReport._default_manager.filter(status='pending').count()
        resolved_count = IncidentReport._default_manager.filter(status='resolved').count()
        
        return {
            'total_incidents': total_incidents,
            'incidents_by_status': by_status,
            'incidents_by_type': by_type,
            'incidents_by_priority': by_priority,
            'pending_incidents': pending_count,
            'resolved_incidents': resolved_count
        }