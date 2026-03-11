# agents/product_agent/pipeline.py
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from products.models import Product
from tasks.models import AgentTask, InboundEmail
from agents.product_agent.validator import load_and_validate
from agents.product_agent.generator import generate_product_content
from django.utils import timezone
import datetime


def run_product_pipeline(
    attachment_path: str,
    scheduled_at: datetime.datetime,
    inbound_email: InboundEmail = None
) -> AgentTask:
    """
    商品上新 Agent 主流程：
    1. 读取并校验 Excel/CSV
    2. Claude 生成标题和描述
    3. 保存商品到数据库
    4. 创建 AgentTask（待人工确认）
    返回创建的 AgentTask
    """
    print(f"\n🚀 启动商品上新 Pipeline")
    print(f"   附件：{attachment_path}")
    print(f"   计划执行时间：{scheduled_at}\n")

    # 1. 读取并校验
    ready, pending = load_and_validate(attachment_path)
    print(f"📊 校验完成：可生成 {len(ready)} 条，待补充 {len(pending)} 条\n")

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
                "generated_title":  content.title if content else "",
                "generated_desc":   content.description if content else "",
                "missing_fields":   [],
                "status":           Product.Status.PENDING,
                "scheduled_at":     scheduled_at,
            }
        )
        product_ids.append(product.id)
        action = "新建" if created else "更新"
        print(f"  {action} 商品：{product.sku} - {product.generated_title}")

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
        print(f"  ⚠ 待补充：{product.sku}，缺少 {validation_result.missing_required}")

    # 3. 创建 AgentTask（状态为待确认）
    agent_task = AgentTask.objects.create(
        task_type    = AgentTask.TaskType.PRODUCT_PUBLISH,
        status       = AgentTask.Status.PENDING,
        scheduled_at = scheduled_at,
        payload      = {"product_ids": product_ids, "attachment": attachment_path},
    )

    print(f"\n✅ Pipeline 完成")
    print(f"   AgentTask ID={agent_task.id}，状态：待人工确认")
    print(f"   请在 Django Admin 确认后任务将在 {scheduled_at} 执行\n")

    return agent_task


# 直接运行测试
if __name__ == "__main__":
    import datetime
    from django.utils import timezone
    scheduled = timezone.now() + datetime.timedelta(minutes=2)
    run_product_pipeline(
        attachment_path="data/sample_products.csv",
        scheduled_at=scheduled,
    )
