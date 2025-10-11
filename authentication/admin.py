from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Voter, Admin, InecOfficial


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['name', 'phone_number', 'role', 'status', 'created_at']
    list_filter = ['role', 'status', 'created_at']
    search_fields = ['name', 'phone_number', 'email']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal info', {'fields': ('name', 'dob')}),
        ('Permissions', {'fields': ('role', 'status', 'is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'name', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ['voter_id', 'get_user_name', 'voters_card_id', 'registration_verified', 'can_vote', 'get_created_date']
    list_filter = ['registration_verified', 'can_vote', 'user__created_at']
    search_fields = ['voter_id', 'voters_card_id', 'user__name', 'user__phone_number']
    actions = ['verify_registration', 'unverify_registration']
    
    def get_user_name(self, obj):
        return obj.user.name
    get_user_name.short_description = 'Name'
    
    def get_created_date(self, obj):
        return obj.user.created_at.strftime('%Y-%m-%d %H:%M')
    get_created_date.short_description = 'Registered'
    
    def verify_registration(self, request, queryset):
        """Mark selected voters as verified"""
        updated = queryset.update(registration_verified=True)
        self.message_user(
            request,
            f'{updated} voter(s) successfully verified.',
            level='SUCCESS'
        )
    verify_registration.short_description = "Verify selected voters"
    
    def unverify_registration(self, request, queryset):
        """Mark selected voters as unverified"""
        updated = queryset.update(registration_verified=False)
        self.message_user(
            request,
            f'{updated} voter(s) marked as unverified.',
            level='WARNING'
        )
    unverify_registration.short_description = "Unverify selected voters"


@admin.register(Admin)
class AdminModelAdmin(admin.ModelAdmin):
    list_display = ['admin_id', 'get_user_name', 'get_user_phone']
    search_fields = ['admin_id', 'user__name', 'user__phone_number']
    
    def get_user_name(self, obj):
        return obj.user.name
    get_user_name.short_description = 'Name'
    
    def get_user_phone(self, obj):
        return obj.user.phone_number
    get_user_phone.short_description = 'Phone Number'


@admin.register(InecOfficial)
class InecOfficialAdmin(admin.ModelAdmin):
    list_display = ['official_id', 'get_user_name', 'get_user_phone']
    search_fields = ['official_id', 'user__name', 'user__phone_number']
    
    def get_user_name(self, obj):
        return obj.user.name
    get_user_name.short_description = 'Name'
    
    def get_user_phone(self, obj):
        return obj.user.phone_number
    get_user_phone.short_description = 'Phone Number'

