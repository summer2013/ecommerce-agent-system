# products/admin.py
from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ['sku', 'name', 'category', 'price', 'status', 'created_at']
    list_filter   = ['status', 'category']
    search_fields = ['sku', 'name']
    readonly_fields = ['missing_fields', 'generated_title', 'generated_desc', 
                       'created_at', 'published_at']