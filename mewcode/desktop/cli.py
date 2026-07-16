from __future__ import annotations

import asyncio
from argparse import Namespace
from pathlib import Path

from mewcode.desktop.policy import DesktopPolicyGuard
from mewcode.desktop.reporting import KnowledgeReportWorkflow
from mewcode.desktop.registry import create_desktop_registry
from mewcode.desktop.service import DesktopTaskService
from mewcode.desktop.skills.document import DocumentSkill
from mewcode.desktop.skills.knowledge import KnowledgeSkill
from mewcode.desktop.trace_store import TaskTraceStore
from mewcode.desktop.workspace import DesktopWorkspace, WorkspaceConfig, WorkspaceError


def run_desktop_foundation(args: Namespace) -> int:
    """运行 Desktop v1 的安全基础入口。

    当前入口只验证用户显式授权的目录、创建 task_id 和 Trace；资料检索、
    文档写入、文件整理会在后续 Skill 注册后接入，不能借此入口绕过策略。
    """
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
    trace_store = TaskTraceStore(workspace)
    service = DesktopTaskService(DesktopPolicyGuard(workspace), trace_store)
    workflow = KnowledgeReportWorkflow(service, KnowledgeSkill(workspace), DocumentSkill(workspace))

    if getattr(args, "desktop_confirm_task", None):
        try:
            task = trace_store.load_task_object(args.desktop_confirm_task)
            workflow.confirm_and_deliver(task, approved=True)
        except (OSError, ValueError) as exc:
            print(f"Desktop delivery error: {exc}", flush=True)
            return 2
        print(f"LocalDesk task delivered: {task.task_id}")
        print(f"status: {task.status.value}")
        print(f"artifact: {task.artifacts[-1].final_path}")
        return 0

    if not args.desktop_task:
        print("Desktop mode requires --desktop-task", flush=True)
        return 2
    task = service.create_task(args.desktop_task)
    if getattr(args, "desktop_report_name", None):
        try:
            if getattr(args, "desktop_grounded_llm", False):
                from mewcode.client import create_client
                from mewcode.config import load_config
                from mewcode.desktop.grounded_renderer import GroundedLLMRenderer

                config = load_config()
                if not config.providers:
                    raise ValueError("没有配置可用模型 provider")
                draft = asyncio.run(workflow.prepare_grounded(task, args.desktop_report_name, GroundedLLMRenderer(create_client(config.providers[0]))))
            else:
                draft = workflow.prepare(task, args.desktop_report_name)
        except ValueError as exc:
            print(f"Desktop report error: {exc}", flush=True)
            return 2
        print(f"LocalDesk report staged: {task.task_id}")
        print(f"status: {task.status.value}")
        print(f"staging: {draft.staged_path}")
        print(f"planned output: {draft.final_path}")
        print(f"citations: {len(draft.source_citations)}")
        print(f"renderer: {'grounded-llm' if getattr(args, 'desktop_grounded_llm', False) else 'deterministic'}")
        print(f"confirm with --desktop-confirm-task {task.task_id}")
        return 0
    print(f"LocalDesk task created: {task.task_id}")
    print(f"status: {task.status.value}")
    print(f"desktop tools registered: {len(registry.list_tools())}")
    print(f"trace: {workspace.task_dir(task.task_id)}")
    print("Foundation mode only: no file operation has been executed.")
    return 0
