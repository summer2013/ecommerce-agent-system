# tasks/models.py
from django.db import models


class AgentTask(models.Model):
    class TaskType(models.TextChoices):
        PRODUCT_PUBLISH   = 'product_publish',   '商品上新'
        STORE_DEACTIVATE  = 'store_deactivate',  '门店下架'

    class Status(models.TextChoices):
        PENDING    = 'pending',    '待确认'
        CONFIRMED  = 'confirmed',  '已确认'
        RUNNING    = 'running',    '执行中'
        DONE       = 'done',       '已完成'
        FAILED     = 'failed',     '失败'
        CANCELLED  = 'cancelled',  '已取消'

    task_type      = models.CharField(max_length=30, choices=TaskType.choices, verbose_name='任务类型')
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name='状态')
    celery_task_id = models.CharField(max_length=255, blank=True, verbose_name='Celery ID')
    scheduled_at   = models.DateTimeField(verbose_name='计划执行时间')
    executed_at    = models.DateTimeField(null=True, blank=True, verbose_name='实际执行时间')
    confirmed_by   = models.CharField(max_length=100, blank=True, verbose_name='确认人')
    payload        = models.JSONField(default=dict, verbose_name='任务参数')
    created_at     = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = 'Agent 任务'
        verbose_name_plural = '任务队列'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_task_type_display()} - {self.scheduled_at}"