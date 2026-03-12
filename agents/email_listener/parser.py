import json
import re
from datetime import datetime
from dataclasses import dataclass

from dateutil import parser as dateparser

from agents.shared.llm import chat_json


@dataclass
class ParsedEmail:
    intent: str  # product_update / store_deactivate / unknown
    scheduled_at: datetime | None  # 解析出的执行时间
    confidence: str  # high / medium / low
    reason: str  # LLM 的判断理由


def parse_email(subject: str, body: str) -> ParsedEmail:
    """
    用 LLM 解析邮件意图和执行时间
    """
    prompt = f"""你是一个电商品牌的邮件分析助手。请分析以下邮件，提取关键信息。

邮件标题：{subject}
邮件正文：{body}

请判断：
1. 这封邮件的意图是什么？
   - product_update：涉及商品上新、商品更新、商品信息变更
   - store_deactivate：涉及门店下架、关闭门店、停止营业
   - unknown：无法判断或不属于以上两类

2. 邮件中提到的执行时间是什么？请务必从标题或正文中抽取出明确的执行时间（例如：2025年3月15日09:00），并转换为“YYYY-MM-DD HH:MM:SS”格式。如果真的完全没有提到任何时间，才返回 null。

3. 你的判断置信度：high / medium / low

返回 JSON 格式：
{{
  "intent": "product_update|store_deactivate|unknown",
  "scheduled_at": "2025-03-15 09:00:00 或 null",
  "confidence": "high|medium|low",
  "reason": "简短说明判断理由"
}}"""

    try:
        raw = chat_json(prompt)
        raw = raw.strip().strip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)

        # 解析时间字符串（先用 LLM 的结果，再用正则兜底）
        scheduled_at = None
        scheduled_raw = data.get("scheduled_at")

        if scheduled_raw and scheduled_raw != "null":
            try:
                scheduled_at = dateparser.parse(scheduled_raw)
            except Exception:
                scheduled_at = None

        # 如果 LLM 没给或解析失败，尝试从原始文本中用正则兜底抽取形如“2026年3月11日16:15”的时间
        if scheduled_at is None:
            text = f"{subject}\n{body}"
            m = re.search(
                r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})",
                text,
            )
            if m:
                year, month, day, hour, minute = map(int, m.groups())
                try:
                    scheduled_at = datetime(year, month, day, hour, minute)
                except ValueError:
                    scheduled_at = None

        return ParsedEmail(
            intent=data.get("intent", "unknown"),
            scheduled_at=scheduled_at,
            confidence=data.get("confidence", "low"),
            reason=data.get("reason", ""),
        )
    except Exception as e:
        print(f"⚠ 解析失败：{e}")
        return ParsedEmail(
            intent="unknown", scheduled_at=None, confidence="low", reason=str(e)
        )


if __name__ == "__main__":
    # 简单本地测试
    tests = [
        (
            "【商品更新】春季新品上新通知",
            "请于2025年3月15日09:00完成以下商品的上新工作，附件为商品清单。",
        ),
        (
            "【商品更新】春季新品上新通知1",
            "请于2026年3月11日16:35完成以下商品的上新工作，附件为商品清单。",
        ),
    ]

    for subject, body in tests:
        print(f"\n📧 标题：{subject}")
        result = parse_email(subject, body)
        print(f"   意图：{result.intent}")
        print(f"   时间：{result.scheduled_at}")
        print(f"   置信度：{result.confidence}")
        print(f"   理由：{result.reason}")