# tasks/admin.py
from django.contrib import admin, messages
from django.utils import timezone
from .models import AgentTask, InboundEmail


@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display    = ['task_type', 'status', 'scheduled_at', 'confirmed_by', 'created_at']
    list_filter     = ['task_type', 'status']
    readonly_fields = ['created_at', 'executed_at', 'celery_task_id']
    actions         = ['confirm_and_schedule', 'confirm_store_deactivate']

    def confirm_and_schedule(self, request, queryset):
        """人工确认并调度任务"""
        from products.tasks import publish_products_task

        confirmed = 0
        for task in queryset.filter(status=AgentTask.Status.PENDING):
            now = timezone.now()
            eta = task.scheduled_at
            countdown = max(0, int((eta - now).total_seconds()))

            celery_task = publish_products_task.apply_async(
                args=[task.id],
                countdown=countdown,
            )

            task.status         = AgentTask.Status.CONFIRMED
            task.confirmed_by   = request.user.username
            task.celery_task_id = celery_task.id
            task.save()
            confirmed += 1

        self.message_user(
            request,
            f"✅ 已确认 {confirmed} 个任务，将在计划时间自动执行",
            messages.SUCCESS
        )

    confirm_and_schedule.short_description = "✅ 确认并调度执行"

    def confirm_store_deactivate(self, request, queryset):
        """人工确认门店下架任务"""
        from stores.tasks import deactivate_stores_task

        confirmed = 0
        for task in queryset.filter(
            status=AgentTask.Status.PENDING,
            task_type=AgentTask.TaskType.STORE_DEACTIVATE,
        ):
            now = timezone.now()
            countdown = max(0, int((task.scheduled_at - now).total_seconds()))

            celery_task = deactivate_stores_task.apply_async(
                args=[task.id],
                countdown=countdown,
            )
            task.status = AgentTask.Status.CONFIRMED
            task.confirmed_by = request.user.username
            task.celery_task_id = celery_task.id
            task.save()
            confirmed += 1

        self.message_user(
            request,
            f"✅ 已确认 {confirmed} 个门店下架任务",
            messages.SUCCESS,
        )

    confirm_store_deactivate.short_description = "🏪 确认门店下架任务"


@admin.register(InboundEmail)
class InboundEmailAdmin(admin.ModelAdmin):
    list_display    = ['sender', 'subject', 'intent', 'parsed_schedule', 'processed', 'received_at']
    list_filter     = ['intent', 'processed']
    readonly_fields = ['received_at', 'raw_body', 'attachment_path']

    def has_add_permission(self, request):
        return False
