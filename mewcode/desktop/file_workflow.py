from __future__ import annotations

from mewcode.desktop.models import ActionKind, PlannedAction, Task, TaskStatus
from mewcode.desktop.service import DesktopTaskService, TaskStateError
from mewcode.desktop.skills.files import FilePlan, FileSkill


class FileOrganizationWorkflow:
    def __init__(self, service: DesktopTaskService, files: FileSkill) -> None: self.service, self.files = service, files

    def prepare(self, task: Task, root: str) -> FilePlan:
        plan = self.files.dry_run(root)
        if plan.conflicts: raise TaskStateError("dry-run 存在冲突，拒绝进入确认")
        actions = [PlannedAction(op.operation_id, "files", ActionKind.MOVE, {"source": op.source, "destination": op.destination}, f"移动到 {op.category}") for op in plan.operations]
        self.service.set_plan(task, "按确定性扩展名规则整理文件", actions)
        self.service.trace_store.append(task.task_id, "file_dry_run", {"total_operations": len(plan.operations), "conflicts": plan.conflicts, "operations": [op.__dict__ for op in plan.operations]})
        return plan

    def confirm_and_execute(self, task: Task, approved: bool) -> None:
        self.service.confirm(task, approved)
        if not approved: return
        ops = [self._op(a) for a in task.actions]
        try:
            done = self.files.execute(ops, self.journal_path(task))
        except Exception as exc:
            self.service.finish(task, str(exc)); raise
        for action in task.actions: action.status = "succeeded"
        self.service.trace_store.append(task.task_id, "file_operations_completed", {"count": len(done), "journal": str(self.journal_path(task))})
        self.service.finish(task)

    def prepare_rollback(self, rollback_task: Task, original_task: Task) -> FilePlan:
        plan = self.files.rollback_plan(self.journal_path(original_task))
        if plan.conflicts: raise TaskStateError("rollback 存在冲突，拒绝进入确认")
        actions = [PlannedAction(op.operation_id, "files", ActionKind.MOVE, {"source": op.source, "destination": op.destination}, "回滚文件移动") for op in plan.operations]
        self.service.set_plan(rollback_task, f"回滚任务 {original_task.task_id} 的已完成操作", actions)
        self.service.trace_store.append(rollback_task.task_id, "rollback_dry_run", {"original_task_id": original_task.task_id, "total_operations": len(plan.operations), "conflicts": plan.conflicts})
        return plan

    def journal_path(self, task: Task): return self.service.trace_store.workspace.task_dir(task.task_id) / "operations.jsonl"
    @staticmethod
    def _op(action: PlannedAction):
        from mewcode.desktop.skills.files import FileOperation
        return FileOperation(action.action_id, action.args["source"], action.args["destination"], action.summary)
