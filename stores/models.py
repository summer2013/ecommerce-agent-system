#  stores/models.py
from django.db import models


class Store(models.Model):
    class Status(models.TextChoices):
        ACTIVE       = 'active',       '正常营业'
        DEACTIVATING = 'deactivating', '下架中'
        INACTIVE     = 'inactive',     '已下架'

    store_code        = models.CharField(max_length=64, unique=True, verbose_name='门店编号')
    name              = models.CharField(max_length=255, verbose_name='门店名称')
    region            = models.CharField(max_length=100, blank=True, verbose_name='地区')
    saleor_channel_id = models.CharField(max_length=128, blank=True, verbose_name='Saleor ID')
    status            = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, verbose_name='状态')
    deactivated_at    = models.DateTimeField(null=True, blank=True, verbose_name='下架时间')
    screenshot_path   = models.CharField(max_length=512, blank=True, verbose_name='验证截图')
    created_at        = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '门店'
        verbose_name_plural = '门店列表'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.store_code} - {self.name}"