# logs/models.py
from django.db import models
from tasks.models import AgentTask


class OperationLog(models.Model):
    class Result(models.TextChoices):
        SUCCESS = 'success', '成功'
        FAILED  = 'failed',  '失败'
        SKIPPED = 'skipped', '已跳过'

    task            = models.ForeignKey(AgentTask, on_delete=models.CASCADE, related_name='logs', verbose_name='关联任务')
    action          = models.CharField(max_length=100, verbose_name='操作类型')
    target_type     = models.CharField(max_length=50, verbose_name='对象类型')
    target_id       = models.CharField(max_length=100, verbose_name='对象ID')
    result          = models.CharField(max_length=20, choices=Result.choices, verbose_name='结果')
    detail          = models.TextField(blank=True, verbose_name='详情')
    screenshot_path = models.CharField(max_length=512, blank=True, verbose_name='截图路径')
    operator        = models.CharField(max_length=100, default='system', verbose_name='操作人')
    created_at      = models.DateTimeField(auto_now_add=True, verbose_name='日志时间')

    class Meta:
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.target_id} - {self.result}"