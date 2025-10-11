from django.contrib import admin
from .models import Vote, VotingSession, Ballot, BallotCandidate


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['vote_id', 'get_voter_name', 'election', 'candidate', 'timestamp', 'is_verified']
    list_filter = ['is_verified', 'timestamp', 'election']
    search_fields = ['voter__user__name', 'election__title', 'candidate__name']
    date_hierarchy = 'timestamp'
    readonly_fields = ['vote_id', 'encrypted_vote_data', 'timestamp']
    
    def get_voter_name(self, obj):
        return obj.voter.user.name
    get_voter_name.short_description = 'Voter'


@admin.register(VotingSession)
class VotingSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'get_voter_name', 'election', 'status', 'started_at', 'completed_at']
    list_filter = ['status', 'started_at']
    search_fields = ['voter__user__name', 'election__title']
    date_hierarchy = 'started_at'
    readonly_fields = ['session_id', 'started_at']
    
    def get_voter_name(self, obj):
        return obj.voter.user.name
    get_voter_name.short_description = 'Voter'


class BallotCandidateInline(admin.TabularInline):
    model = BallotCandidate
    extra = 0
    ordering = ['order']


@admin.register(Ballot)
class BallotAdmin(admin.ModelAdmin):
    list_display = ['ballot_id', 'election', 'get_candidate_count', 'created_at']
    search_fields = ['election__title']
    date_hierarchy = 'created_at'
    readonly_fields = ['ballot_id', 'created_at']
    inlines = [BallotCandidateInline]
    
    def get_candidate_count(self, obj):
        return obj.candidates.count()
    get_candidate_count.short_description = 'Candidates'
