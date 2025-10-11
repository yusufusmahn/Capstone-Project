from django.contrib import admin
from .models import IncidentReport, IncidentEvidence, IncidentResponse


class IncidentEvidenceInline(admin.TabularInline):
    model = IncidentEvidence
    extra = 0
    readonly_fields = ['evidence_id', 'uploaded_at', 'file_size']


class IncidentResponseInline(admin.TabularInline):
    model = IncidentResponse
    extra = 0
    readonly_fields = ['response_id', 'created_at']


@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = ['report_id', 'get_reporter_name', 'incident_type', 'status', 'priority', 'created_at', 'assigned_to']
    list_filter = ['incident_type', 'status', 'priority', 'created_at']
    search_fields = ['reporter__name', 'description', 'location']
    date_hierarchy = 'created_at'
    readonly_fields = ['report_id', 'created_at', 'updated_at']
    inlines = [IncidentEvidenceInline, IncidentResponseInline]
    
    fieldsets = (
        ('Report Information', {
            'fields': ('report_id', 'reporter', 'voter', 'incident_type')
        }),
        ('Details', {
            'fields': ('description', 'location', 'priority')
        }),
        ('Status & Assignment', {
            'fields': ('status', 'assigned_to', 'resolution_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_reporter_name(self, obj):
        return obj.reporter.name
    get_reporter_name.short_description = 'Reporter'


@admin.register(IncidentEvidence)
class IncidentEvidenceAdmin(admin.ModelAdmin):
    list_display = ['evidence_id', 'get_incident_id', 'evidence_type', 'file', 'uploaded_at', 'file_size']
    list_filter = ['evidence_type', 'uploaded_at']
    search_fields = ['incident__report_id', 'description']
    readonly_fields = ['evidence_id', 'uploaded_at', 'file_size']
    
    def get_incident_id(self, obj):
        return obj.incident.report_id
    get_incident_id.short_description = 'Incident ID'


@admin.register(IncidentResponse)
class IncidentResponseAdmin(admin.ModelAdmin):
    list_display = ['response_id', 'get_incident_id', 'responder', 'action_type', 'created_at']
    list_filter = ['action_type', 'created_at']
    search_fields = ['incident__report_id', 'responder__user__name', 'description']
    readonly_fields = ['response_id', 'created_at']
    
    def get_incident_id(self, obj):
        return obj.incident.report_id
    get_incident_id.short_description = 'Incident ID'
