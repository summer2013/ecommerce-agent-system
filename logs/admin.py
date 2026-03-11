# logs/admin.py
from django.contrib import admin
from .models import OperationLog


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display  = ['action', 'target_type', 'target_id', 'result', 'operator', 'created_at']
    list_filter   = ['result', 'target_type', 'action']
    readonly_fields = ['created_at']

    def has_add_permission(self, request):
        return False  # 日志只读，不允许手动新增

    def has_delete_permission(self, request, obj=None):
        return False  # 日志不允许删除（审计要求）
