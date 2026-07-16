from __future__ import annotations

from collections.abc import Iterable

from mewcode.desktop.models import PlannedAction, Task, TaskStatus, TERMINAL_STATUSES
from mewcode.desktop.policy import DesktopPolicyGuard
from mewcode.desktop.trace_store import TaskTraceStore


_ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.DRAFT: {TaskStatus.PLANNED, TaskStatus.CANCELLED},
    TaskStatus.PLANNED: {TaskStatus.AWAITING_CONFIRMATION, TaskStatus.EXECUTING, TaskStatus.CANCELLED},
    TaskStatus.AWAITING_CONFIRMATION: {TaskStatus.EXECUTING, TaskStatus.CANCELLED},
    TaskStatus.EXECUTING: {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.SUCCEEDED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


class TaskStateError(ValueError):
    pass


class DesktopTaskService:
    def __init__(self, policy: DesktopPolicyGuard, trace_store: TaskTraceStore) -> None:
        self.policy = policy
        self.trace_store = trace_store

    def create_task(self, user_query: str) -> Task:
        if not user_query.strip():
            raise ValueError("任务描述不能为空")
        task = Task.create(user_query)
        self.trace_store.create(task)
        return task

    def set_plan(self, task: Task, plan: str, actions: Iterable[PlannedAction]) -> None:
        self._transition(task, TaskStatus.PLANNED)
        task.plan = plan
        task.actions = list(actions)
        decisions = []
        needs_confirmation = False
        denied = False
        for action in task.actions:
            decision = self.policy.evaluate(action)
            action.requires_confirmation = decision.requires_confirmation
            action.status = "blocked" if decision.effect == "deny" else "pending"
            decisions.append({"action_id": action.action_id, **decision.__dict__})
            needs_confirmation = needs_confirmation or decision.requires_confirmation
            denied = denied or decision.effect == "deny"
        task.touch()
        self.trace_store.save_task(task)
        self.trace_store.append(task.task_id, "plan_created", {"plan": plan, "decisions": decisions})
        if denied:
            task.error = "计划包含被安全策略拒绝的动作"
            task.touch()
            self.trace_store.save_task(task)
            self.trace_store.append(task.task_id, "policy_rejected", {"decisions": decisions})
            return
        if needs_confirmation:
            self._transition(task, TaskStatus.AWAITING_CONFIRMATION)

    def confirm(self, task: Task, approved: bool) -> None:
        if task.status != TaskStatus.AWAITING_CONFIRMATION:
            raise TaskStateError("当前任务不在等待确认状态")
        self.trace_store.append(task.task_id, "confirmation", {"approved": approved})
        self._transition(task, TaskStatus.EXECUTING if approved else TaskStatus.CANCELLED)

    def finish(self, task: Task, error: str | None = None) -> None:
        if task.status != TaskStatus.EXECUTING:
            raise TaskStateError("只有执行中的任务可以完成")
        if error:
            task.error = error
            self._transition(task, TaskStatus.FAILED)
        else:
            self._transition(task, TaskStatus.SUCCEEDED)

    def _transition(self, task: Task, target: TaskStatus) -> None:
        if task.status in TERMINAL_STATUSES or target not in _ALLOWED_TRANSITIONS[task.status]:
            raise TaskStateError(f"不允许任务状态从 {task.status.value} 转为 {target.value}")
        previous = task.status
        task.status = target
        task.touch()
        self.trace_store.save_task(task)
        self.trace_store.append(
            task.task_id,
            "status_changed",
            {"from": previous.value, "to": target.value},
        )
