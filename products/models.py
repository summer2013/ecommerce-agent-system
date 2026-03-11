# products/models.py
from django.db import models


class Product(models.Model):
    class Status(models.TextChoices):
        DRAFT      = 'draft',      '草稿（字段缺失）'
        PENDING    = 'pending',    '待人工确认'
        REVIEWING  = 'reviewing',  '待执行'
        PUBLISHED  = 'published',  '已上新'

    sku               = models.CharField(max_length=64, unique=True, verbose_name='SKU')
    name              = models.CharField(max_length=255, blank=True, verbose_name='商品名')
    category          = models.CharField(max_length=100, blank=True, verbose_name='品类')
    spec              = models.CharField(max_length=255, blank=True, verbose_name='规格')
    price             = models.DecimalField(max_digits=10, decimal_places=2, null=True, verbose_name='售价')
    generated_title   = models.CharField(max_length=100, blank=True, verbose_name='生成标题')
    generated_desc    = models.TextField(blank=True, verbose_name='生成描述')
    missing_fields    = models.JSONField(default=list, verbose_name='缺失字段')
    status            = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name='状态')
    scheduled_at      = models.DateTimeField(null=True, blank=True, verbose_name='计划上新时间')
    published_at      = models.DateTimeField(null=True, blank=True, verbose_name='实际上新时间')
    created_at        = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品列表'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sku} - {self.name}"