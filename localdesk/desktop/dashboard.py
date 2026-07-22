"""零前端依赖的只读任务看板：直接渲染 task.json 与 events.jsonl。"""

from __future__ import annotations

import html
from pathlib import Path

from localdesk.desktop.trace_store import TaskTraceStore


def render_task_board(store: TaskTraceStore) -> Path:
    rows: list[str] = []
    for task_dir in sorted(store.workspace.task_root.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True):
        if not task_dir.is_dir() or not (task_dir / "task.json").exists():
            continue
        task = store.load_task_object(task_dir.name)
        events = store.load_events(task.task_id)
        artifacts = "<br>".join(html.escape(item.final_path or item.staged_path or "") for item in task.artifacts) or "—"
        last_event = events[-1]["event_type"] if events else "—"
        rows.append(f"<tr><td>{html.escape(task.task_id)}</td><td>{html.escape(task.status.value)}</td><td>{html.escape(task.user_query)}</td><td>{len(task.actions)}</td><td>{html.escape(last_event)}</td><td>{artifacts}</td></tr>")
    document = """<!doctype html><meta charset='utf-8'><title>LocalDesk Task Board</title>
<style>body{font-family:Segoe UI,Arial;margin:32px;background:#f8fafc;color:#172033}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #dbe3ef;padding:10px;text-align:left;vertical-align:top}th{background:#eaf1fb}</style>
<h1>LocalDesk Task Board</h1><p>只读：数据直接来自 task.json 和 events.jsonl，不包含聊天壳或虚构状态。</p>
<table><thead><tr><th>Task ID</th><th>状态</th><th>任务</th><th>动作数</th><th>最后事件</th><th>产物</th></tr></thead><tbody>""" + "\n".join(rows) + "</tbody></table>"
    target = store.workspace.task_root / "task_board.html"
    target.write_text(document, encoding="utf-8", newline="\n")
    return target
