from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

from mewcode.desktop.skills.knowledge import SourceChunk
from mewcode.desktop.workspace import DesktopWorkspace, WorkspaceError


@dataclass(frozen=True)
class StagedDraft:
    staged_path: str
    final_path: str
    sha256: str
    source_citations: list[str]
    summary: str


class DocumentSkill:
    def __init__(self, workspace: DesktopWorkspace) -> None:
        self.workspace = workspace

    def stage_markdown(self, task_id: str, title: str, query: str, chunks: list[SourceChunk], filename: str) -> StagedDraft:
        name = _safe_markdown_filename(filename)
        staged, final = self.workspace.task_dir(task_id) / "staging" / name, self.workspace.output_root / name
        if final.exists():
            raise WorkspaceError(f"禁止覆盖已有文件: {final}")
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text(_render_markdown(title, query, chunks), encoding="utf-8", newline="\n")
        return StagedDraft(str(staged), str(final), _sha256(staged), [chunk.citation() for chunk in chunks], f"基于 {len(chunks)} 个可定位资料片段生成 Markdown 草稿")

    def commit(self, draft: StagedDraft) -> None:
        staged, final = Path(draft.staged_path), Path(draft.final_path)
        if not self.workspace.can_write_artifact(staged) or not self.workspace.can_write_artifact(final):
            raise WorkspaceError("草稿或交付目标超出允许写入范围")
        if not staged.exists():
            raise WorkspaceError("staging 草稿不存在")
        if _sha256(staged) != draft.sha256:
            raise WorkspaceError("staging 草稿哈希已变化，确认失效")
        if final.exists():
            raise WorkspaceError(f"禁止覆盖已有文件: {final}")
        final.parent.mkdir(parents=True, exist_ok=True)
        temporary = final.with_suffix(final.suffix + ".tmp")
        temporary.write_bytes(staged.read_bytes())
        os.replace(temporary, final)


def _safe_markdown_filename(filename: str) -> str:
    name = Path(filename).name
    if name != filename or not name or name in {".", ".."}:
        raise WorkspaceError("产物文件名必须是不含目录的文件名")
    if not name.lower().endswith(".md"):
        name += ".md"
    if not re.fullmatch(r"[\w.\-\u4e00-\u9fff ]+", name):
        raise WorkspaceError("产物文件名包含不允许的字符")
    return name


def _render_markdown(title: str, query: str, chunks: list[SourceChunk]) -> str:
    lines = [f"# {title}", "", f"> 任务：{query}", "", "## 资料摘要", ""]
    if not chunks:
        lines.extend(["未在授权资料中检索到相关内容。", ""])
    for number, chunk in enumerate(chunks, start=1):
        excerpt = " ".join(chunk.text.split())
        lines.extend([f"### 资料片段 {number}", "", excerpt[:277] + ("..." if len(excerpt) > 280 else ""), "", f"来源：`{chunk.citation()}`", ""])
    lines.extend(["## Sources", ""])
    lines.extend(f"- `{chunk.citation()}`" for chunk in chunks) if chunks else lines.append("- 无命中资料")
    lines.append("")
    return "\n".join(lines)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
