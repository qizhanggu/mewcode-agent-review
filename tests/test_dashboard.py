from pathlib import Path

from localdesk.desktop.dashboard import render_task_board
from localdesk.desktop.policy import DesktopPolicyGuard
from localdesk.desktop.service import DesktopTaskService
from localdesk.desktop.trace_store import TaskTraceStore
from localdesk.desktop.workspace import DesktopWorkspace, WorkspaceConfig


def test_task_board_renders_real_task_state(tmp_path: Path) -> None:
    source, output, tasks = tmp_path / "source", tmp_path / "output", tmp_path / "tasks"
    for path in (source, output, tasks): path.mkdir()
    workspace = DesktopWorkspace(WorkspaceConfig(read_roots=[source], output_root=output, task_root=tasks))
    store = TaskTraceStore(workspace)
    service = DesktopTaskService(DesktopPolicyGuard(workspace), store)
    task = service.create_task("real trace task")
    board = render_task_board(store)
    text = board.read_text(encoding="utf-8")
    assert task.task_id in text and "real trace task" in text and "draft" in text
