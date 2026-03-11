import os
import random
import time

from dotenv import load_dotenv

load_dotenv()

SALEOR_API_URL = os.getenv("SALEOR_API_URL", "")
SALEOR_TOKEN = os.getenv("SALEOR_TOKEN", "")

# Mock 模式：没有真实 Saleor 环境时使用
MOCK_MODE = not SALEOR_API_URL


def deactivate_channel(channel_id: str) -> dict:
    """
    调用 Saleor GraphQL API 下架门店（关闭渠道）
    Mock 模式下模拟 API 响应
    """
    if MOCK_MODE:
        return _mock_deactivate(channel_id)
    return _real_deactivate(channel_id)


def _mock_deactivate(channel_id: str) -> dict:
    """Mock 实现：模拟 API 调用延迟和结果"""
    time.sleep(0.5)  # 模拟网络延迟

    # 模拟 95% 成功率
    success = random.random() > 0.05

    if success:
        return {
            "success": True,
            "channel_id": channel_id,
            "message": f"[MOCK] 渠道 {channel_id} 已成功停用",
        }
    return {
        "success": False,
        "channel_id": channel_id,
        "message": f"[MOCK] 渠道 {channel_id} 停用失败：模拟网络错误",
    }


def _real_deactivate(channel_id: str) -> dict:
    """真实 Saleor GraphQL 实现（有真实环境时启用）"""
    import requests

    mutation = """
    mutation DeactivateChannel($id: ID!) {
        channelDeactivate(id: $id) {
            channel { id isActive }
            errors { field message }
        }
    }
    """
    try:
        resp = requests.post(
            SALEOR_API_URL,
            json={"query": mutation, "variables": {"id": channel_id}},
            headers={"Authorization": f"Bearer {SALEOR_TOKEN}"},
            timeout=10,
        )
        data = resp.json()
        errors = data.get("data", {}).get("channelDeactivate", {}).get("errors", [])
        if errors:
            return {"success": False, "channel_id": channel_id, "message": str(errors)}
        return {"success": True, "channel_id": channel_id, "message": "下架成功"}
    except Exception as e:
        return {"success": False, "channel_id": channel_id, "message": str(e)}
