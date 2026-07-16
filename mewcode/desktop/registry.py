from __future__ import annotations

from mewcode.tools import ToolRegistry


def create_desktop_registry() -> ToolRegistry:
    """返回空的 Desktop Registry。

    Phase 1 先证明旧 Coding 工具不会泄漏进 Desktop 模式；后续阶段只向
    此 Registry 注册经过 DesktopPolicyGuard 约束的 Skill 工具。
    """

    return ToolRegistry()
