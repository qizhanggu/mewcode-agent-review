from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mewcode.desktop.models import ActionKind, PlannedAction
from mewcode.desktop.workspace import DesktopWorkspace, WorkspaceError


@dataclass(frozen=True)
class PolicyDecision:
    effect: str
    reason: str
    requires_confirmation: bool = False


class DesktopPolicyGuard:
    """位于 Planner 与文件系统操作之间的 deny-first 策略层。"""

    _DENIED_KINDS = {ActionKind.DELETE, ActionKind.SHELL, ActionKind.NETWORK}

    def __init__(self, workspace: DesktopWorkspace) -> None:
        self.workspace = workspace

    def evaluate(self, action: PlannedAction) -> PolicyDecision:
        if action.kind in self._DENIED_KINDS:
            return PolicyDecision("deny", f"Desktop v1 不允许 {action.kind.value}")

        try:
            if action.kind == ActionKind.READ:
                return self._evaluate_read(action.args)
            if action.kind == ActionKind.WRITE:
                return self._evaluate_write(action.args)
            if action.kind in {ActionKind.MOVE, ActionKind.RENAME}:
                return self._evaluate_manage(action.args, action.kind)
        except WorkspaceError as exc:
            return PolicyDecision("deny", str(exc))
        return PolicyDecision("deny", f"未知或未实现的动作类型: {action.kind.value}")

    def _evaluate_read(self, args: dict[str, Any]) -> PolicyDecision:
        path = self._required_path(args, "path")
        if not self.workspace.can_read(path):
            return PolicyDecision("deny", f"读取路径越出授权范围: {path}")
        return PolicyDecision("allow", "授权目录内的只读操作")

    def _evaluate_write(self, args: dict[str, Any]) -> PolicyDecision:
        destination = self._required_path(args, "destination")
        if not self.workspace.can_write_artifact(destination):
            return PolicyDecision("deny", f"写入目标不在 staging 或 output 目录: {destination}")
        if Path(destination).exists():
            return PolicyDecision("deny", f"禁止覆盖已有文件: {destination}")
        return PolicyDecision("ask", "写入产物需要确认", requires_confirmation=True)

    def _evaluate_manage(self, args: dict[str, Any], kind: ActionKind) -> PolicyDecision:
        source = self._required_path(args, "source")
        destination = self._required_path(args, "destination")
        if not self.workspace.can_manage(source):
            return PolicyDecision("deny", f"{kind.value} 源路径不在可整理目录: {source}")
        if not self.workspace.can_manage(destination):
            return PolicyDecision("deny", f"{kind.value} 目标路径不在可整理目录: {destination}")
        if Path(destination).exists():
            return PolicyDecision("deny", f"禁止覆盖已有文件: {destination}")
        return PolicyDecision("ask", f"{kind.value} 需要用户确认", requires_confirmation=True)

    @staticmethod
    def _required_path(args: dict[str, Any], name: str) -> str:
        value = args.get(name)
        if not isinstance(value, str) or not value.strip():
            raise WorkspaceError(f"缺少路径参数: {name}")
        return value
