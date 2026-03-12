# agents/product_agent/pipeline.py
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from products.models import Product
from tasks.models import AgentTask, InboundEmail
from agents.shared.logger import get_logger
from agents.product_agent.validator import load_and_validate
from agents.product_agent.generator import generate_product_content
from django.utils import timezone
import datetime

logger = get_logger(__name__)


def run_product_pipeline(
    attachment_path: str,
    scheduled_at: datetime.datetime,
    inbound_email: InboundEmail = None
) -> AgentTask | None:
    """
    商品上新 Agent 主流程。
    标题和描述直接读取 Excel（法务审核过，不调用 LLM）。
    返回创建的 AgentTask，供后续 Celery 调度使用。
    失败时返回 None 并记录失败任务。
    """
    try:
        logger.info("启动商品上新 Pipeline，附件=%s，计划执行时间=%s", attachment_path, scheduled_at)

        # 1. 读取并校验
        ready, pending = load_and_validate(attachment_path)
        logger.info("校验完成：可生成 %s 条，待补充 %s 条", len(ready), len(pending))

        # 2. 生成内容并保存到数据库
        product_ids = []
        for validation_result in ready:
            row = validation_result.data
            content = generate_product_content(
                category=str(row.get("category", "")),
                spec=str(row.get("spec", "")),
                price=float(row.get("price", 0)),
                extra_info=str(row.get("extra_info", "")),
            )

            # 存入数据库（有则更新，无则创建）
            product, created = Product.objects.update_or_create(
                sku=str(row.get("sku")),
                defaults={
                    "name":             str(row.get("name", "")),
                    "category":         str(row.get("category", "")),
                    "spec":             str(row.get("spec", "")),
                    "price":            float(row.get("price", 0)),
                    "generated_title": str(row.get("title", "")),
                    "generated_desc":  str(row.get("description", "")),
                    "missing_fields":   [],
                    "status":           Product.Status.PENDING,
                    "scheduled_at":     scheduled_at,
                }
            )
            product_ids.append(product.id)
            action = "新建" if created else "更新"
            logger.info("%s商品：%s - %s", action, product.sku, product.generated_title)

        # 处理缺失字段的商品（标记为 draft）
        for validation_result in pending:
            row = validation_result.data
            product, _ = Product.objects.update_or_create(
                sku=str(row.get("sku")),
                defaults={
                    "name":           str(row.get("name", "")),
                    "status":         Product.Status.DRAFT,
                    "missing_fields": validation_result.missing_required,
                }
            )
            logger.warning("待补充：%s，缺少 %s", product.sku, validation_result.missing_required)

        # 3. 创建 AgentTask（状态为待确认）
        agent_task = AgentTask.objects.create(
            task_type    = AgentTask.TaskType.PRODUCT_PUBLISH,
            status       = AgentTask.Status.PENDING,
            scheduled_at = scheduled_at,
            payload      = {"product_ids": product_ids, "attachment": attachment_path},
        )

        logger.info("Pipeline 完成，AgentTask ID=%s，状态：待人工确认，计划执行时间=%s", agent_task.id, scheduled_at)

        return agent_task
    except Exception as e:
        logger.exception("商品上新 Pipeline 异常：%s", e)
        AgentTask.objects.create(
            task_type    = AgentTask.TaskType.PRODUCT_PUBLISH,
            status       = AgentTask.Status.FAILED,
            scheduled_at = scheduled_at,
            payload      = {"error": str(e), "attachment": attachment_path},
        )
        return None


# 直接运行测试
if __name__ == "__main__":
    import datetime
    from django.utils import timezone
    scheduled = timezone.now() + datetime.timedelta(minutes=2)
    run_product_pipeline(
        attachment_path="data/sample_products.csv",
        scheduled_at=scheduled,
    )
