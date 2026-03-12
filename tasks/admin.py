# tasks/admin.py
from django.contrib import admin, messages
from django.utils import timezone
from .models import AgentTask, InboundEmail


@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display    = ['task_type', 'status', 'scheduled_at', 'confirmed_by', 'created_at']
    list_filter     = ['task_type', 'status']
    readonly_fields = ['created_at', 'executed_at', 'celery_task_id', 'payload']
    actions         = ['confirm_tasks']

    def confirm_tasks(self, request, queryset):
        """统一确认入口，根据任务类型分发到对应 Celery 任务"""
        from products.tasks import publish_products_task
        from stores.tasks import deactivate_stores_task

        confirmed = 0
        skipped   = 0

        for task in queryset.filter(status=AgentTask.Status.PENDING):
            countdown = max(0, int((task.scheduled_at - timezone.now()).total_seconds()))

            if task.task_type == AgentTask.TaskType.PRODUCT_PUBLISH:
                celery_task = publish_products_task.apply_async(
                    args=[task.id], countdown=countdown
                )
            elif task.task_type == AgentTask.TaskType.STORE_DEACTIVATE:
                celery_task = deactivate_stores_task.apply_async(
                    args=[task.id], countdown=countdown
                )
            else:
                skipped += 1
                continue

            task.status         = AgentTask.Status.CONFIRMED
            task.confirmed_by   = request.user.username
            task.celery_task_id = celery_task.id
            task.save()
            confirmed += 1

        msg = f"✅ 已确认 {confirmed} 个任务"
        if skipped:
            msg += f"，跳过 {skipped} 个未知类型"
        self.message_user(request, msg, messages.SUCCESS)

    confirm_tasks.short_description = "✅ 确认并调度执行"


@admin.register(InboundEmail)
class InboundEmailAdmin(admin.ModelAdmin):
    list_display    = ['sender', 'subject', 'intent', 'parsed_schedule', 'processed', 'received_at']
    list_filter     = ['intent', 'processed']
    readonly_fields = ['received_at', 'raw_body', 'attachment_path']

    def has_add_permission(self, request):
        return False