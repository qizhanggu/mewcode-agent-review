from __future__ import annotations

from dataclasses import asdict

from mewcode.desktop.models import ActionKind, Artifact, PlannedAction, Task, TaskStatus
from mewcode.desktop.grounded_renderer import GroundedLLMRenderer, GroundedRenderError
from mewcode.desktop.service import DesktopTaskService, TaskStateError
from mewcode.desktop.skills.document import DocumentSkill, StagedDraft
from mewcode.desktop.skills.knowledge import KnowledgeSkill


class KnowledgeReportWorkflow:
    """将资料检索和 Markdown staging 串入同一条受控任务链。"""

    def __init__(self, service: DesktopTaskService, knowledge: KnowledgeSkill, document: DocumentSkill) -> None:
        self.service = service
        self.knowledge = knowledge
        self.document = document

    def prepare(self, task: Task, filename: str, title: str | None = None) -> StagedDraft:
        if task.status != TaskStatus.DRAFT:
            raise TaskStateError("只有 draft 任务可以准备报告")
        indexed = self.knowledge.index()
        chunks = self.knowledge.search(task.user_query)
        draft = self.document.stage_markdown(
            task.task_id,
            title or "LocalDesk 资料报告草稿",
            task.user_query,
            chunks,
            filename,
        )
        action = PlannedAction(
            action_id="deliver-markdown",
            skill="document",
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
            skill="grounded_document",
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
            self.document.commit(draft)
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
