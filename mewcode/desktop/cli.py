from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from mewcode.desktop.policy import DesktopPolicyGuard
from mewcode.desktop.registry import create_desktop_registry
from mewcode.desktop.service import DesktopTaskService
from mewcode.desktop.trace_store import TaskTraceStore
from mewcode.desktop.workspace import DesktopWorkspace, WorkspaceConfig, WorkspaceError


def run_desktop_foundation(args: Namespace) -> int:
    """运行 Desktop v1 的安全基础入口。

    当前入口只验证用户显式授权的目录、创建 task_id 和 Trace；资料检索、
    文档写入、文件整理会在后续 Skill 注册后接入，不能借此入口绕过策略。
    """
    if not args.desktop_task:
        print("Desktop mode requires --desktop-task", flush=True)
        return 2
    if not args.desktop_read_root:
        print("Desktop mode requires at least one --desktop-read-root", flush=True)
        return 2
    if not args.desktop_output_root or not args.desktop_task_root:
        print("Desktop mode requires --desktop-output-root and --desktop-task-root", flush=True)
        return 2

    try:
        workspace = DesktopWorkspace(
            WorkspaceConfig(
                read_roots=[Path(item) for item in args.desktop_read_root],
                managed_roots=[Path(item) for item in args.desktop_managed_root],
                output_root=Path(args.desktop_output_root),
                task_root=Path(args.desktop_task_root),
            )
        )
    except WorkspaceError as exc:
        print(f"Desktop workspace error: {exc}", flush=True)
        return 2

    registry = create_desktop_registry()
    service = DesktopTaskService(DesktopPolicyGuard(workspace), TaskTraceStore(workspace))
    task = service.create_task(args.desktop_task)
    print(f"LocalDesk task created: {task.task_id}")
    print(f"status: {task.status.value}")
    print(f"desktop tools registered: {len(registry.list_tools())}")
    print(f"trace: {workspace.task_dir(task.task_id)}")
    print("Foundation mode only: no file operation has been executed.")
    return 0
