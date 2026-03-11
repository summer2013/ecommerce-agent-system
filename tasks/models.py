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


class InboundEmail(models.Model):
    class Intent(models.TextChoices):
        PRODUCT_UPDATE   = 'product_update',   '商品更新'
        STORE_DEACTIVATE = 'store_deactivate', '门店下架'
        UNKNOWN          = 'unknown',          '未知'

    subject          = models.CharField(max_length=512, verbose_name='邮件标题')
    sender           = models.CharField(max_length=255, verbose_name='发件人')
    intent           = models.CharField(max_length=30, choices=Intent.choices, default=Intent.UNKNOWN, verbose_name='意图')
    parsed_schedule  = models.DateTimeField(null=True, blank=True, verbose_name='解析出的执行时间')
    attachment_path  = models.CharField(max_length=512, blank=True, verbose_name='附件路径')
    raw_body         = models.TextField(blank=True, verbose_name='邮件正文')
    received_at      = models.DateTimeField(verbose_name='收件时间')
    processed        = models.BooleanField(default=False, verbose_name='已处理')

    class Meta:
        verbose_name = '收件记录'
        verbose_name_plural = '收件记录'
        ordering = ['-received_at']

    def __str__(self):
        return f"{self.sender} - {self.subject}"