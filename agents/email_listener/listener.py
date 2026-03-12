# agents/email_listener/listener.py
import os
import sys
import time
from pathlib import Path

import django
import pandas as pd
from django.utils import timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from tasks.models import AgentTask, InboundEmail
from stores.models import Store
from agents.shared.logger import get_logger
from agents.shared.email_client import fetch_unread_emails
from agents.email_listener.parser import parse_email
from agents.product_agent.pipeline import run_product_pipeline

logger = get_logger(__name__)

ATTACHMENT_DIR = Path("attachments")
ATTACHMENT_DIR.mkdir(exist_ok=True)

KEYWORDS = ["商品更新", "门店下架"]


def save_attachment(filename: str, data: bytes) -> str:
    path = ATTACHMENT_DIR / filename
    with open(path, "wb") as f:
        f.write(data)
    return str(path)


def handle_product_update(attachment_path: str, scheduled_at, inbound: InboundEmail):
    """处理商品更新邮件"""
    logger.info("触发商品上新 Pipeline")
    run_product_pipeline(
        attachment_path=attachment_path,
        scheduled_at=scheduled_at,
        inbound_email=inbound,
    )


def handle_store_deactivate(attachment_path: str, scheduled_at, inbound: InboundEmail):
    """处理门店下架邮件"""
    logger.info("触发门店下架 Pipeline")

    # 读取附件里的门店列表
    try:
        df = pd.read_csv(attachment_path)
    except Exception:
        df = pd.read_excel(attachment_path)

    store_codes = df["store_code"].tolist()

    # 同步门店数据到数据库
    for _, row in df.iterrows():
        Store.objects.get_or_create(
            store_code=str(row["store_code"]),
            defaults={
                "name":              str(row.get("name", "")),
                "region":            str(row.get("region", "")),
                "saleor_channel_id": str(row.get("saleor_channel_id", "")),
            }
        )

    # 创建 AgentTask（待人工确认）
    agent_task = AgentTask.objects.create(
        task_type    = AgentTask.TaskType.STORE_DEACTIVATE,
        status       = AgentTask.Status.PENDING,
        scheduled_at = scheduled_at,
        payload      = {"store_codes": store_codes, "attachment": attachment_path},
    )
    logger.info("AgentTask ID=%s，等待人工确认", agent_task.id)


def process_email(raw_email: dict) -> InboundEmail | None:
    """
    处理单封邮件的完整流程：
    1. LLM 解析意图和执行时间
    2. 保存附件到本地
    3. 写入收件记录（InboundEmail）
    4. 根据意图触发对应 Pipeline
    - product_update  → 商品上新 Pipeline
    - store_deactivate → 门店下架 LangGraph
    """
    subject = raw_email["subject"]
    body    = raw_email["body"]

    logger.info("处理邮件：%s", subject)

    # LLM 解析意图和执行时间
    parsed = parse_email(subject, body)
    logger.info("意图：%s（%s），执行时间：%s", parsed.intent, parsed.confidence, parsed.scheduled_at)

    # 保存附件
    attachment_path = ""
    supported = (".xlsx", ".xls", ".csv")
    for att in raw_email.get("attachments", []):
        if att["filename"].endswith(supported):
            attachment_path = save_attachment(att["filename"], att["data"])
        else:
            logger.warning("不支持的附件格式：%s，已跳过", att["filename"])

    existing = InboundEmail.objects.filter(
        subject=subject,
        sender=raw_email["sender"],
        received_at__date=raw_email["received_at"].date()
    ).first()

    if existing and existing.processed:
        logger.warning("该邮件已处理过，跳过")
        return existing

    # 写入收件记录
    inbound = InboundEmail.objects.create(
        subject         = subject,
        sender          = raw_email["sender"],
        intent          = parsed.intent,
        parsed_schedule = parsed.scheduled_at,
        attachment_path = attachment_path,
        raw_body        = body,
        received_at     = raw_email["received_at"],
    )

    # 根据意图触发对应 Pipeline（必须同时有附件和执行时间）
    if not attachment_path:
        logger.warning("无附件，跳过")
        return inbound

    if not parsed.scheduled_at:
        logger.warning("未解析到执行时间，跳过")
        return inbound

    if parsed.intent == "product_update":
        handle_product_update(attachment_path, parsed.scheduled_at, inbound)

    elif parsed.intent == "store_deactivate":
        handle_store_deactivate(attachment_path, parsed.scheduled_at, inbound)

    else:
        logger.warning("未识别的意图：%s，跳过", parsed.intent)

    # 标记邮件为已处理
    inbound.processed = True
    inbound.save()

    return inbound


def run_once():
    logger.info("开始检查收件箱")
    new_emails = []
    for keyword in KEYWORDS:
        emails = fetch_unread_emails(keyword=keyword)
        new_emails.extend(emails)

    if not new_emails:
        logger.info("暂无新邮件")
        return

    logger.info("发现 %s 封相关邮件", len(new_emails))
    for raw in new_emails:
        try:
            process_email(raw)
        except Exception as e:
            logger.exception("处理邮件失败：%s，跳过继续处理下一封", e)


def run_forever(interval_seconds: int = 60):
    """
    持续轮询收件箱（仅调试用，手动触发时可调用）。
    生产环境使用 Celery Beat 定时触发 poll_email_task，见 agents/email_listener/tasks.py。
    """
    while True:
        run_once()
        logger.info("等待 %s 秒后再次检查", interval_seconds)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_once()
    # 默认每 60 秒轮询一次（生产用 Celery Beat，调试时可取消注释）
    # run_forever(60)