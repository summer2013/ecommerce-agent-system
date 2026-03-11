# stores/admin.py
from django.contrib import admin
from .models import Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display  = ['store_code', 'name', 'region', 'status', 'deactivated_at']
    list_filter   = ['status', 'region']
    search_fields = ['store_code', 'name']
    readonly_fields = ['created_at', 'deactivated_at']