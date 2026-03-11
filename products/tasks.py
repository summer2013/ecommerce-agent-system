# products/tasks.py
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def publish_products_task(self, agent_task_id: int):
    """
    执行商品上新的 Celery 任务
    agent_task_id: AgentTask 的数据库 ID
    """
    from tasks.models import AgentTask
    from products.models import Product
    from logs.models import OperationLog

    try:
        agent_task = AgentTask.objects.get(id=agent_task_id)
        agent_task.status = AgentTask.Status.RUNNING
        agent_task.executed_at = timezone.now()
        agent_task.save()

        # 从 payload 里取出要上新的商品 ID 列表
        product_ids = agent_task.payload.get("product_ids", [])
        products = Product.objects.filter(id__in=product_ids)

        success_count = 0
        fail_count = 0

        for product in products:
            try:
                # 模拟上新操作（Week 4 先用 mock，后续接真实 API）
                product.status = Product.Status.PUBLISHED
                product.published_at = timezone.now()
                product.save()

                # 写操作日志
                OperationLog.objects.create(
                    task=agent_task,
                    action="product_publish",
                    target_type="product",
                    target_id=product.sku,
                    result=OperationLog.Result.SUCCESS,
                    detail=f"商品 {product.sku} 上新成功",
                    operator="system",
                )
                success_count += 1
                logger.info(f"商品上新成功：{product.sku}")

            except Exception as e:
                fail_count += 1
                OperationLog.objects.create(
                    task=agent_task,
                    action="product_publish",
                    target_type="product",
                    target_id=product.sku,
                    result=OperationLog.Result.FAILED,
                    detail=str(e),
                    operator="system",
                )

        # 更新任务状态
        agent_task.status = AgentTask.Status.DONE
        agent_task.save()
        logger.info(f"任务完成：成功 {success_count} 条，失败 {fail_count} 条")

    except Exception as exc:
        logger.error(f"任务执行异常：{exc}")
        raise self.retry(exc=exc, countdown=60)  # 60秒后重试
