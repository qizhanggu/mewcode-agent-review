from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

from localdesk.desktop.models import ActionKind, Artifact, PlannedAction, Task, TaskStatus
from localdesk.desktop.grounded_renderer import GroundedLLMRenderer, GroundedRenderError
from localdesk.desktop.registry import DesktopToolRegistry, create_desktop_registry
from localdesk.desktop.reviewer import DeterministicReviewer
from localdesk.desktop.service import DesktopTaskService, TaskStateError
from localdesk.desktop.skills.document import DocumentSkill, StagedDraft
from localdesk.desktop.skills.knowledge import KnowledgeSkill

if TYPE_CHECKING:
    from localdesk.desktop.browser import BrowserAdapter, WebChunk


class KnowledgeReportWorkflow:
    """将资料检索和 Markdown staging 串入同一条受控任务链。"""

    def __init__(self, service: DesktopTaskService, knowledge: KnowledgeSkill, document: DocumentSkill, registry: DesktopToolRegistry | None = None) -> None:
        self.service = service
        self.knowledge = knowledge
        self.document = document
        self.registry = registry or create_desktop_registry(service)

    def prepare(
        self,
        task: Task,
        filename: str,
        title: str | None = None,
        browser: "BrowserAdapter | None" = None,
        web_urls: list[str] | None = None,
    ) -> StagedDraft:
        if task.status != TaskStatus.DRAFT:
            raise TaskStateError("只有 draft 任务可以准备报告")
        search_action = PlannedAction(
            action_id="knowledge-search",
            skill="knowledge.search",
            kind=ActionKind.READ,
            args={"path": str(self.knowledge.workspace.read_roots[0]), "query": task.user_query},
            summary="检索授权的本地资料并返回可定位引用",
        )
        indexed, chunks = self.registry.execute(
            task,
            search_action,
            lambda: (self.knowledge.index(), self.knowledge.search(task.user_query)),
            verify=lambda result: isinstance(result[0], int) and isinstance(result[1], list),
        )
        evidence: list[object] = list(chunks)
        for position, url in enumerate(web_urls or [], start=1):
            if browser is None:
                raise TaskStateError("网页研究需要 Browser adapter")
            web_action = PlannedAction(
                action_id=f"browser-open-{position}",
                skill="browser.open",
                kind=ActionKind.NAVIGATE,
                args={"url": url},
                summary="读取授权域名内的公开网页并保留引用",
            )
            evidence.append(self.registry.execute(
                task,
                web_action,
                lambda url=url: browser.open(url),
                verify=lambda result: self.knowledge.workspace.can_browse(result.url) and bool(result.text and result.accessed_at),
            ))
        staged_path, _ = self.document.draft_paths(task.task_id, filename)
        stage_action = PlannedAction(
            action_id="stage-markdown",
            skill="document.stage_markdown",
            kind=ActionKind.WRITE,
            args={"destination": str(staged_path)},
            summary="将带引用的 Markdown 草稿写入任务 staging",
        )
        draft = self.registry.execute(
            task,
            stage_action,
            lambda: self.document.stage_markdown(task.task_id, title or "LocalDesk 资料报告草稿", task.user_query, evidence, filename),
            verify=lambda result: Path(result.staged_path).exists() and result.sha256 != "",
        )
        review = DeterministicReviewer().review_markdown(draft.staged_path, evidence)
        self.service.trace_store.append(task.task_id, "review_completed", {"reviewer": "deterministic", "approved": review.approved, "findings": review.findings})
        if not review.approved:
            self.service.fail(task, "; ".join(review.findings), event_type="review_rejected")
            raise TaskStateError("草稿未通过确定性 Reviewer")
        action = PlannedAction(
            action_id="deliver-markdown",
            skill="document.commit_markdown",
            kind=ActionKind.WRITE,
            args={"destination": draft.final_path},
            summary="确认后交付 staging Markdown 草稿到 output 目录",
            preview={
                "staged_path": draft.staged_path,
                "sha256": draft.sha256,
                "citations": draft.source_citations,
                "indexed_chunks": indexed,
            },
        )
        self.service.set_plan(task, "检索授权资料并生成 Markdown 草稿；确认后交付到 output。", [action])
        self.service.trace_store.append(task.task_id, "knowledge_searched", {"query": task.user_query, "indexed_chunks": indexed, "citations": draft.source_citations})
        self.service.trace_store.append(task.task_id, "draft_staged", asdict(draft))
        return draft

    async def prepare_grounded(self, task: Task, filename: str, renderer: GroundedLLMRenderer) -> StagedDraft:
        if task.status != TaskStatus.DRAFT:
            raise TaskStateError("只有 draft 任务可以准备报告")
        indexed = self.knowledge.index()
        chunks = self.knowledge.search(task.user_query)
        try:
            rendered = await renderer.render(task.user_query, chunks)
            draft = self.document.stage_grounded_markdown(task.task_id, task.user_query, rendered.report, chunks, filename)
        except (GroundedRenderError, ValueError) as exc:
            self.service.fail(task, str(exc), event_type="llm_render_failed")
            raise
        action = PlannedAction(
            action_id="deliver-markdown",
            skill="document.commit_markdown",
            kind=ActionKind.WRITE,
            args={"destination": draft.final_path},
            summary="确认后交付带可验证引用的 LLM Markdown 草稿到 output 目录",
            preview={"staged_path": draft.staged_path, "sha256": draft.sha256, "citations": draft.source_citations, "indexed_chunks": indexed},
        )
        self.service.set_plan(task, "检索授权资料，由 LLM 基于给定片段生成结构化报告；确认后交付到 output。", [action])
        self.service.trace_store.append(task.task_id, "llm_rendered", {"title": rendered.report.title, "sections": [{"heading": item.heading, "citation_ids": item.citation_ids} for item in rendered.report.sections]})
        self.service.trace_store.append(task.task_id, "knowledge_searched", {"query": task.user_query, "indexed_chunks": indexed, "citations": draft.source_citations})
        self.service.trace_store.append(task.task_id, "draft_staged", asdict(draft))
        return draft

    def confirm_and_deliver(self, task: Task, approved: bool) -> None:
        self.service.confirm(task, approved)
        if not approved:
            return
        action = self._delivery_action(task)
        preview = action.preview
        draft = StagedDraft(
            staged_path=preview["staged_path"],
            final_path=action.args["destination"],
            sha256=preview["sha256"],
            source_citations=preview["citations"],
            summary="确认后的 Markdown 交付",
        )
        try:
            self.registry.execute(
                task,
                action,
                lambda: self.document.commit(draft),
                verify=lambda _result: Path(draft.final_path).exists(),
            )
        except Exception as exc:
            self.service.finish(task, error=str(exc))
            raise
        action.status = "succeeded"
        self.service.add_artifact(task, Artifact(
            kind="markdown",
            staged_path=draft.staged_path,
            final_path=draft.final_path,
            sha256=draft.sha256,
            summary=draft.summary,
        ))
        self.service.finish(task)

    @staticmethod
    def _delivery_action(task: Task) -> PlannedAction:
        for action in task.actions:
            if action.action_id == "deliver-markdown":
                return action
        raise TaskStateError("任务中不存在 Markdown 交付动作")
