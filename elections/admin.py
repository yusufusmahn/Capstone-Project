from django.contrib import admin
from .models import Election, Candidate


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'status', 'start_date', 'end_date', 'created_by']
    list_filter = ['type', 'status', 'start_date']
    search_fields = ['title', 'description']
    date_hierarchy = 'start_date'
    ordering = ['-start_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'type', 'description')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'status')
        }),
        ('Administration', {
            'fields': ('created_by',)
        }),
    )


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'party', 'position', 'election', 'get_vote_count']
    list_filter = ['party', 'position', 'election__type', 'created_at']
    search_fields = ['name', 'party', 'election__title']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'party', 'position', 'biography', 'photo')
        }),
        ('Election', {
            'fields': ('election',)
        }),
    )
    
    def get_vote_count(self, obj):
        return obj.get_vote_count()
    get_vote_count.short_description = 'Votes'
