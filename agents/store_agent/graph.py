import os
import sys
import operator
from typing import Annotated, TypedDict

import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone
from langgraph.graph import END, StateGraph

from agents.shared.logger import get_logger
from agents.shared.saleor_client import deactivate_channel

logger = get_logger(__name__)
from agents.shared.screenshot import take_mock_screenshot
from agents.shared.email_client import send_email
from logs.models import OperationLog
from stores.models import Store
from tasks.models import AgentTask


class StoreDeactivateState(TypedDict):
    agent_task_id: int
    stores: list
    current_index: int
    results: Annotated[list, operator.add]
    report: str


def load_stores_node(state: StoreDeactivateState) -> StoreDeactivateState:
    agent_task = AgentTask.objects.get(id=state["agent_task_id"])
    store_codes = agent_task.payload.get("store_codes", [])
    stores = list(
        Store.objects.filter(store_code__in=store_codes).values(
            "id", "store_code", "name", "saleor_channel_id"
        )
    )
    logger.info("待下架门店：%s 家", len(stores))
    return {**state, "stores": stores, "current_index": 0, "results": []}


def deactivate_store_node(state: StoreDeactivateState) -> StoreDeactivateState:
    idx = state["current_index"]
    store = state["stores"][idx]

    logger.info("[%s/%s] 处理：%s（%s）", idx + 1, len(state["stores"]), store["name"], store["store_code"])

    api_result = deactivate_channel(store["saleor_channel_id"])
    logger.info("API 结果：%s", "成功" if api_result["success"] else "失败")

    screenshot_path = take_mock_screenshot(store["store_code"], store["name"])

    Store.objects.filter(store_code=store["store_code"]).update(
        status=Store.Status.INACTIVE if api_result["success"] else Store.Status.ACTIVE,
        deactivated_at=timezone.now() if api_result["success"] else None,
        screenshot_path=screenshot_path,
    )

    agent_task = AgentTask.objects.get(id=state["agent_task_id"])
    OperationLog.objects.create(
        task=agent_task,
        action="store_deactivate",
        target_type="store",
        target_id=store["store_code"],
        result=OperationLog.Result.SUCCESS if api_result["success"] else OperationLog.Result.FAILED,
        detail=api_result["message"],
        screenshot_path=screenshot_path,
        operator="system",
    )

    result = {
        "store_code": store["store_code"],
        "name": store["name"],
        "success": api_result["success"],
        "message": api_result["message"],
        "screenshot": screenshot_path,
    }

    return {**state, "current_index": idx + 1, "results": [result]}


def should_continue(state: StoreDeactivateState) -> str:
    if state["current_index"] < len(state["stores"]):
        return "deactivate"
    return "generate_report"


def generate_report_node(state: StoreDeactivateState) -> StoreDeactivateState:
    results = state["results"]
    success = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    report_lines = [
        "=" * 40,
        "门店下架执行报告",
        "=" * 40,
        f"总计：{len(results)} 家",
        f"成功：{len(success)} 家",
        f"失败：{len(failed)} 家",
        "",
        "详细结果：",
    ]

    for r in results:
        status = "✅" if r["success"] else "❌"
        report_lines.append(f"  {status} {r['store_code']} {r['name']} - {r['message']}")

    report = "\n".join(report_lines)
    logger.info("门店下架报告：%s", report)

    AgentTask.objects.filter(id=state["agent_task_id"]).update(status=AgentTask.Status.DONE)

    agent_task = AgentTask.objects.get(id=state["agent_task_id"])
    reply_to = agent_task.payload.get("reply_to") or os.getenv("EMAIL_ADDRESS")
    if reply_to:
        ok = send_email(
            to=reply_to,
            subject="【门店下架执行报告】已完成",
            body=report,
        )
        if ok:
            logger.info("结果报告已自动回复")
        else:
            logger.warning("结果报告发送失败")

    return {**state, "report": report}


def run_store_deactivate_graph(agent_task_id: int):
    """
    执行门店下架 LangGraph。
    异常时打印错误、将对应 AgentTask 标记为 FAILED 并重新抛出（供 Celery 重试）。
    """
    try:
        graph = build_store_deactivate_graph()
        return graph.invoke(
            {
                "agent_task_id": agent_task_id,
                "stores": [],
                "current_index": 0,
                "results": [],
                "report": "",
            }
        )
    except Exception as e:
        logger.exception("门店下架 Pipeline 异常：%s", e)
        task = AgentTask.objects.filter(id=agent_task_id).first()
        if task:
            payload = dict(task.payload) if task.payload else {}
            payload["error"] = str(e)
            task.status = AgentTask.Status.FAILED
            task.payload = payload
            task.save(update_fields=["status", "payload"])
        raise


def build_store_deactivate_graph():
    """
    构建门店下架 LangGraph。
    节点：load_stores → deactivate（循环）→ generate_report
    条件边：每家门店处理完后判断是否还有待处理门店。
    失败自动重试最多 3 次，最终失败写入操作日志。
    """
    graph = StateGraph(StoreDeactivateState)

    graph.add_node("load_stores", load_stores_node)
    graph.add_node("deactivate", deactivate_store_node)
    graph.add_node("generate_report", generate_report_node)

    graph.set_entry_point("load_stores")

    graph.add_edge("load_stores", "deactivate")
    graph.add_conditional_edges(
        "deactivate",
        should_continue,
        {
            "deactivate": "deactivate",
            "generate_report": "generate_report",
        },
    )
    graph.add_edge("generate_report", END)

    return graph.compile()


if __name__ == "__main__":
    for code, name, channel in [
        ("STORE001", "上海旗舰店", "channel-shanghai-001"),
        ("STORE002", "北京王府井店", "channel-beijing-001"),
    ]:
        Store.objects.get_or_create(
            store_code=code,
            defaults={"name": name, "saleor_channel_id": channel},
        )

    task = AgentTask.objects.create(
        task_type=AgentTask.TaskType.STORE_DEACTIVATE,
        status=AgentTask.Status.CONFIRMED,
        scheduled_at=timezone.now(),
        payload={"store_codes": ["STORE001", "STORE002"]},
    )

    logger.info("启动门店下架 Agent，任务 ID=%s", task.id)
    graph = build_store_deactivate_graph()
    _final_state = graph.invoke(
        {
            "agent_task_id": task.id,
            "stores": [],
            "current_index": 0,
            "results": [],
            "report": "",
        }
    )

    logger.info("执行完成")
