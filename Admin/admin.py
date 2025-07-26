from django.contrib import admin
from .models import APIList, AccessToken

@admin.register(APIList)
class APIListAdmin(admin.ModelAdmin):
    list_display = ('endpoint', 'description', 'access_count', 'last_accessed', 'created_at')
    search_fields = ('endpoint', 'description')
    list_filter = ('created_at', 'last_accessed')
    readonly_fields = ('created_at', 'updated_at', 'last_accessed', 'access_count') # These should be updated programmatically

admin.site.register(AccessToken)