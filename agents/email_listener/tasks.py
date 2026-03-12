# agents/email_listener/tasks.py
from celery import shared_task
from agents.shared.logger import get_logger

logger = get_logger(__name__)


@shared_task(name="agents.email_listener.tasks.poll_email_task")
def poll_email_task():
    """
    Celery Beat 定时触发的邮件轮询任务。
    每 60 秒执行一次，检查收件箱是否有新的触发邮件。
    """
    logger.info("开始轮询收件箱...")
    try:
        from agents.email_listener.listener import run_once
        run_once()
    except Exception as e:
        logger.error("邮件轮询异常：%s", e)
