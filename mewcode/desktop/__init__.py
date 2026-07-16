"""LocalDesk Agent 的受控桌面任务运行时。

该包与原有 Coding Agent 并存。Desktop v1 只暴露经过工作区和策略层
约束的能力，绝不复用默认 Coding Registry 中的 Bash 或编辑工具。
"""

from mewcode.desktop.models import (
    Artifact,
    PlannedAction,
    Task,
    TaskStatus,
    TraceEvent,
)
from mewcode.desktop.policy import DesktopPolicyGuard, PolicyDecision
from mewcode.desktop.service import DesktopTaskService
from mewcode.desktop.workspace import DesktopWorkspace, WorkspaceConfig

__all__ = [
    "Artifact",
    "DesktopPolicyGuard",
    "DesktopTaskService",
    "DesktopWorkspace",
    "PlannedAction",
    "PolicyDecision",
    "Task",
    "TaskStatus",
    "TraceEvent",
    "WorkspaceConfig",
]
