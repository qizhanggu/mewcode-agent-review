from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from localdesk.desktop.policy import DesktopPolicyGuard
from localdesk.desktop.cli import run_desktop_foundation
from localdesk.desktop.reporting import KnowledgeReportWorkflow
from localdesk.desktop.service import DesktopTaskService
from localdesk.desktop.skills.document import DocumentSkill
from localdesk.desktop.skills.knowledge import KnowledgeSkill
from localdesk.desktop.trace_store import TaskTraceStore
from localdesk.desktop.workspace import DesktopWorkspace, WorkspaceConfig, WorkspaceError
from localdesk.desktop.browser import FakeBrowserAdapter, WebChunk


@pytest.fixture
def workspace(tmp_path: Path) -> DesktopWorkspace:
    sources, output, tasks = tmp_path / "sources", tmp_path / "output", tmp_path / "tasks"
    for directory in (sources, output, tasks):
        directory.mkdir()
    return DesktopWorkspace(WorkspaceConfig(read_roots=[sources], output_root=output, task_root=tasks))


@pytest.fixture
def workflow(workspace: DesktopWorkspace) -> KnowledgeReportWorkflow:
    service = DesktopTaskService(DesktopPolicyGuard(workspace), TaskTraceStore(workspace))
    return KnowledgeReportWorkflow(service, KnowledgeSkill(workspace, chunk_lines=2), DocumentSkill(workspace))


def test_search_to_staging_then_confirmed_delivery(workspace: DesktopWorkspace, workflow: KnowledgeReportWorkflow) -> None:
    (workspace.read_roots[0] / "meeting.md").write_text(
        "Project Orion weekly meeting\nOwner: Alice\nMilestone is Friday\nRisk: API delay\n",
        encoding="utf-8",
    )
    task = workflow.service.create_task("Summarize Project Orion milestone risk")
    draft = workflow.prepare(task, "weekly-report.md", title="Weekly Report")

    assert task.status.value == "awaiting_confirmation"
    assert Path(draft.staged_path).exists()
    assert not Path(draft.final_path).exists()
    staged = Path(draft.staged_path).read_text(encoding="utf-8")
    assert "meeting.md (lines" in staged
    assert "## Sources" in staged

    workflow.confirm_and_deliver(task, approved=True)
    assert task.status.value == "succeeded"
    assert Path(draft.final_path).exists()
    assert task.artifacts[0].sha256 == draft.sha256
    events = workflow.service.trace_store.load_events(task.task_id)
    assert "knowledge_searched" in [event["event_type"] for event in events]
    assert "draft_staged" in [event["event_type"] for event in events]
    assert "artifact_committed" in [event["event_type"] for event in events]
    assert {"tool_requested", "tool_policy_decided", "tool_completed", "tool_verified"}.issubset(
        {event["event_type"] for event in events}
    )


def test_rejected_confirmation_never_writes_output(workspace: DesktopWorkspace, workflow: KnowledgeReportWorkflow) -> None:
    (workspace.read_roots[0] / "note.txt").write_text("weekly report source", encoding="utf-8")
    task = workflow.service.create_task("weekly report")
    draft = workflow.prepare(task, "rejected.md")
    workflow.confirm_and_deliver(task, approved=False)
    assert task.status.value == "cancelled"
    assert Path(draft.staged_path).exists()
    assert not Path(draft.final_path).exists()


def test_authorized_web_evidence_is_reviewed_and_cited(workspace: DesktopWorkspace, workflow: KnowledgeReportWorkflow) -> None:
    workspace.browser_allowed_domains = ("jobs.example.com",)
    (workspace.read_roots[0] / "resume.md").write_text("Agent project experience", encoding="utf-8")
    url = "https://jobs.example.com/agent-role"
    browser = FakeBrowserAdapter({url: WebChunk("web:role", url, "Agent Role", "Need Python and Agent workflow experience", "2026-07-20T00:00:00+00:00")})
    task = workflow.service.create_task("compare Agent role requirements")
    draft = workflow.prepare(task, "job-match.md", browser=browser, web_urls=[url])
    content = Path(draft.staged_path).read_text(encoding="utf-8")
    assert "Agent Role (https://jobs.example.com/agent-role" in content
    events = workflow.service.trace_store.load_events(task.task_id)
    assert any(event["event_type"] == "review_completed" and event["payload"]["approved"] for event in events)


def test_changed_staging_invalidates_confirmation(workspace: DesktopWorkspace, workflow: KnowledgeReportWorkflow) -> None:
    (workspace.read_roots[0] / "note.txt").write_text("important project update", encoding="utf-8")
    task = workflow.service.create_task("project update")
    draft = workflow.prepare(task, "tampered.md")
    Path(draft.staged_path).write_text("tampered", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="哈希"):
        workflow.confirm_and_deliver(task, approved=True)
    assert task.status.value == "failed"
    assert not Path(draft.final_path).exists()


def test_pdf_page_citation(workspace: DesktopWorkspace, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePage:
        def extract_text(self) -> str:
            return "PDF project decision"

    class FakeReader:
        def __init__(self, _path: str) -> None:
            self.pages = [FakePage()]

    monkeypatch.setattr("pypdf.PdfReader", FakeReader)
    (workspace.read_roots[0] / "minutes.pdf").write_bytes(b"not-a-real-pdf")
    skill = KnowledgeSkill(workspace)
    assert skill.index() == 1
    hit = skill.search("project")
    assert hit[0].citation() == "minutes.pdf (page 1)"


def test_extracts_text_from_real_minimal_pdf(workspace: DesktopWorkspace) -> None:
    pdf = workspace.read_roots[0] / "real.pdf"
    _write_text_pdf(pdf, "Launch milestone Friday")
    skill = KnowledgeSkill(workspace)
    skill.index()
    hit = skill.search("milestone")
    assert hit[0].source_path == "real.pdf"
    assert hit[0].locator == "page 1"
    assert "Launch milestone Friday" in hit[0].text


def test_existing_output_is_not_overwritten(workspace: DesktopWorkspace, workflow: KnowledgeReportWorkflow) -> None:
    (workspace.read_roots[0] / "note.txt").write_text("source", encoding="utf-8")
    (workspace.output_root / "existing.md").write_text("keep", encoding="utf-8")
    task = workflow.service.create_task("source")
    with pytest.raises(WorkspaceError, match="禁止覆盖"):
        workflow.prepare(task, "existing.md")
    assert (workspace.output_root / "existing.md").read_text(encoding="utf-8") == "keep"


def test_cli_stages_then_confirms_in_separate_invocations(workspace: DesktopWorkspace, capsys: pytest.CaptureFixture[str]) -> None:
    (workspace.read_roots[0] / "note.md").write_text("Orion release is Friday", encoding="utf-8")
    base = {
        "desktop_read_root": [str(workspace.read_roots[0])],
        "desktop_managed_root": [],
        "desktop_output_root": str(workspace.output_root),
        "desktop_task_root": str(workspace.task_root),
    }
    assert run_desktop_foundation(Namespace(**base, desktop_task="Orion release", desktop_report_name="orion.md", desktop_confirm_task=None)) == 0
    task_id = next(workspace.task_root.iterdir()).name
    assert not (workspace.output_root / "orion.md").exists()
    assert run_desktop_foundation(Namespace(**base, desktop_task=None, desktop_report_name=None, desktop_confirm_task=task_id)) == 0
    assert (workspace.output_root / "orion.md").exists()
    assert "delivered" in capsys.readouterr().out


def _write_text_pdf(path: Path, text: str) -> None:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 5 0 R >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    body = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body.extend(f"{number} 0 obj\n".encode("ascii"))
        body.extend(obj)
        body.extend(b"\nendobj\n")
    xref_offset = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    body.extend(b"0000000000 65535 f \n")
    body.extend(b"".join(f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets[1:]))
    body.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    path.write_bytes(body)
