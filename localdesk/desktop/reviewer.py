from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class CitableEvidence(Protocol):
    def citation(self) -> str: ...


@dataclass(frozen=True)
class ReviewResult:
    approved: bool
    findings: list[str]


class DeterministicReviewer:
    """不依赖 LLM 的交付前检查；不能批准或扩大任何高风险动作。"""

    _SENSITIVE_PATTERNS = (r"api[_-]?key", r"authorization:\s*bearer", r"password\s*=")

    def review_markdown(self, path: str, evidence: list[CitableEvidence]) -> ReviewResult:
        text = Path(path).read_text(encoding="utf-8")
        findings: list[str] = []
        if not text.strip():
            findings.append("草稿为空")
        if "## Sources" not in text:
            findings.append("草稿缺少 Sources 章节")
        if not evidence:
            findings.append("没有可用于交付的本地或网页证据")
        for item in evidence:
            if item.citation() not in text:
                findings.append(f"草稿缺少证据引用: {item.citation()}")
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in self._SENSITIVE_PATTERNS):
            findings.append("草稿疑似包含敏感字段")
        return ReviewResult(approved=not findings, findings=findings)
