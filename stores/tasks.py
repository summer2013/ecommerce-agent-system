import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def deactivate_stores_task(self, agent_task_id: int):
    """
    门店下架 Celery 任务
    触发 LangGraph 流程执行
    """
    try:
        from django.utils import timezone

        from agents.store_agent.graph import run_store_deactivate_graph
        from tasks.models import AgentTask

        agent_task = AgentTask.objects.get(id=agent_task_id)
        agent_task.status = AgentTask.Status.RUNNING
        agent_task.executed_at = timezone.now()
        agent_task.save()

        final_state = run_store_deactivate_graph(agent_task_id)

        logger.info(f"门店下架任务完成：{agent_task_id}")
        return final_state["report"]
    except Exception as exc:
        logger.error(f"门店下架任务失败：{exc}")
        raise self.retry(exc=exc, countdown=60)
