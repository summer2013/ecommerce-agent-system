# tasks/admin.py
from django.contrib import admin
from .models import AgentTask
from .models import AgentTask, InboundEmail

@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display  = ['task_type', 'status', 'scheduled_at', 'confirmed_by', 'created_at']
    list_filter   = ['task_type', 'status']
    readonly_fields = ['created_at', 'executed_at', 'celery_task_id']


@admin.register(InboundEmail)
class InboundEmailAdmin(admin.ModelAdmin):
    list_display  = ['sender', 'subject', 'intent', 'parsed_schedule', 'processed', 'received_at']
    list_filter   = ['intent', 'processed']
    readonly_fields = ['received_at', 'raw_body', 'attachment_path']

    def has_add_permission(self, request):
        return False  # 收件记录只由系统创建