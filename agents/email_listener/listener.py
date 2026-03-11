# agents/email_listener/listener.py
import os
import django
import sys

# 设置 Django 环境（因为这个脚本独立运行，需要手动初始化）
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from tasks.models import InboundEmail
from agents.shared.email_client import fetch_unread_emails
from agents.email_listener.parser import parse_email
from pathlib import Path

# 附件保存目录
ATTACHMENT_DIR = Path("attachments")
ATTACHMENT_DIR.mkdir(exist_ok=True)

# 监听的关键词
KEYWORDS = ["商品更新", "门店下架"]


def save_attachment(filename: str, data: bytes) -> str:
    """保存附件到本地，返回路径"""
    path = ATTACHMENT_DIR / filename
    with open(path, "wb") as f:
        f.write(data)
    return str(path)


def process_email(raw_email: dict) -> InboundEmail | None:
    """
    处理单封邮件：
    1. LLM 解析意图和时间
    2. 保存附件
    3. 写入数据库
    """
    subject = raw_email["subject"]
    body    = raw_email["body"]

    print(f"  📧 处理：{subject}")

    # LLM 解析
    parsed = parse_email(subject, body)
    print(f"     意图：{parsed.intent}（{parsed.confidence}）")

    # 保存附件
    attachment_path = ""
    for att in raw_email.get("attachments", []):
        if att["filename"].endswith((".xlsx", ".xls", ".csv")):
            attachment_path = save_attachment(att["filename"], att["data"])
            print(f"     附件：{attachment_path}")

    # 写入数据库
    inbound = InboundEmail.objects.create(
        subject         = subject,
        sender          = raw_email["sender"],
        intent          = parsed.intent,
        parsed_schedule = parsed.scheduled_at,
        attachment_path = attachment_path,
        raw_body        = body,
        received_at     = raw_email["received_at"],
    )
    print(f"     ✅ 已存入数据库 ID={inbound.id}")

    # 根据意图触发对应 Pipeline
    from agents.product_agent.pipeline import run_product_pipeline
    if parsed.intent == "product_update" and attachment_path and parsed.scheduled_at:
        print(f"     🚀 触发商品上新 Pipeline...")
        run_product_pipeline(
            attachment_path=attachment_path,
            scheduled_at=parsed.scheduled_at,
            inbound_email=inbound,
        )

    return inbound


def run_once():
    """执行一次邮件检查"""
    print("🔍 开始检查收件箱...")
    new_emails = []

    # 分别用关键词过滤拉取
    for keyword in KEYWORDS:
        emails = fetch_unread_emails(keyword=keyword)
        new_emails.extend(emails)

    if not new_emails:
        print("  暂无新邮件")
        return

    print(f"  发现 {len(new_emails)} 封相关邮件\n")
    for raw in new_emails:
        process_email(raw)


if __name__ == "__main__":
    run_once()