# config/celery.py
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("ecommerce_agent")

# 从 Django settings 读取 Celery 配置（以 CELERY_ 开头的配置项）
app.config_from_object("django.conf:settings", namespace="CELERY")

# 自动发现所有 app 里的 tasks.py
app.autodiscover_tasks()
