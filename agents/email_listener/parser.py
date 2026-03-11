# agents/email_listener/parser.py
import json
from datetime import datetime
from dateutil import parser as dateparser
from dataclasses import dataclass
from agents.shared.llm import chat_json


@dataclass
class ParsedEmail:
    intent: str           # product_update / store_deactivate / unknown
    scheduled_at: datetime | None  # 解析出的执行时间
    confidence: str       # high / medium / low
    reason: str           # LLM 的判断理由


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

2. 邮件中提到的执行时间是什么？（如果没有明确时间，返回 null）

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
        raw = raw.strip().strip('`')
        if raw.startswith('json'):
            raw = raw[4:].strip()
        data = json.loads(raw)

        # 解析时间字符串
        scheduled_at = None
        if data.get("scheduled_at") and data["scheduled_at"] != "null":
            try:
                scheduled_at = dateparser.parse(data["scheduled_at"])
            except:
                pass

        return ParsedEmail(
            intent=data.get("intent", "unknown"),
            scheduled_at=scheduled_at,
            confidence=data.get("confidence", "low"),
            reason=data.get("reason", ""),
        )
    except Exception as e:
        print(f"⚠ 解析失败：{e}")
        return ParsedEmail(intent="unknown", scheduled_at=None, confidence="low", reason=str(e))


# 直接运行测试
if __name__ == "__main__":
    # 模拟两种邮件测试
    test_cases = [
        {
            "subject": "【商品更新】春季新品上新通知",
            "body": "请于2025年3月15日09:00完成以下商品的上新工作，附件为商品清单。"
        },
        {
            "subject": "门店下架通知 - 华南区",
            "body": "由于品牌收缩策略，请于本月20日24:00前完成以下门店的下架操作，详见附件。"
        },
    ]

    for t in test_cases:
        print(f"\n📧 标题：{t['subject']}")
        result = parse_email(t["subject"], t["body"])
        print(f"   意图：{result.intent}")
        print(f"   时间：{result.scheduled_at}")
        print(f"   置信度：{result.confidence}")
        print(f"   理由：{result.reason}")