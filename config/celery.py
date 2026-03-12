# config/celery.py
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("ecommerce_agent")

# 从 Django settings 读取 Celery 配置（以 CELERY_ 开头的配置项）
app.config_from_object("django.conf:settings", namespace="CELERY")

# 自动发现所有 app 里的 tasks.py（含 agents.email_listener）
from django.conf import settings
app.autodiscover_tasks(lambda: list(settings.INSTALLED_APPS) + ["agents.email_listener"])

# Beat 调度：每 60 秒轮询邮件
app.conf.beat_schedule = {
    "poll-email-every-60s": {
        "task": "agents.email_listener.tasks.poll_email_task",
        "schedule": 60.0,  # 每 60 秒触发一次
    },
}

app.conf.timezone = "Asia/Shanghai"
