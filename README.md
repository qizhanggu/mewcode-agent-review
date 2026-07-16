# LocalDesk Agent

面向用户**明确授权本地目录**的受控 Desktop Agent：检索本地资料、生成带引用的 Markdown 草稿、经确认后交付；并提供已测试的确定性文件整理与回滚工作流核心模块。

## 来源与独立改造范围

本仓库基于 MewCode Python Coding Agent 学习型底座改造。原始代码及来源标注保留，不宣称从零开发。本人独立完成的 LocalDesk 改造集中在 `mewcode/desktop/`：任务状态机、路径授权、deny-first Policy Guard、Trace、资料检索、staging/哈希确认交付、Grounded LLM 渲染约束、文件整理与回滚核心工作流、测试与文档。

## 架构

```text
用户任务
  -> Knowledge Skill（仅 read_roots，返回 citation_id）
  -> Deterministic / Grounded LLM Renderer（只接收检索片段）
  -> Document Skill（task staging + SHA-256）
  -> Policy Guard + 独立确认
  -> output_root 交付 + task Trace

managed_roots -> FileOrganizationWorkflow（dry-run -> 确认 -> journal -> 独立确认回滚）
```

## 安全模型

| 目录 | 权限 |
|---|---|
| `read_roots` | 仅检索资料 |
| `managed_roots` | 仅确定性整理流程在确认后 move/rename |
| `output_root` | 仅确认后交付 Markdown |
| `task_root` | task.json、events.jsonl、staging、operation journal |

越权、覆盖、删除、Shell、网络操作直接拒绝。所有写入先 staging；确认前 output 零副作用，确认时复核草稿 SHA-256。每个任务有 task_id、计划、策略决定、确认和产物 Trace。

## 当前能力与非目标

- 支持 MD/TXT/可提取文本 PDF 的轻量检索，引用定位到行号或页码。
- 支持确定性带引用 Markdown 草稿和确认交付。
- 支持 Grounded LLM JSON 渲染：每段必须给出本次检索内真实 citation_id；幻觉引用、无引用、解析失败、超时均拒绝暂存。
- 已实现并测试 `FileOrganizationWorkflow`：dry-run、串行 move、operation journal、独立确认回滚。**它不是已完成的 CLI 用户入口。**
- 不支持：任意 Shell、删除、覆盖、浏览器、MCP、多 Agent、Electron、真实 GUI 自动化、扫描件 OCR。

## 无敏感报告 Demo

创建仅含构造资料的目录，按 [report_demo.md](docs/report_demo.md) 执行两步：第一次仅 staging，第二次携带 task_id 才交付。真实模型需额外加 `--desktop-grounded-llm`，且仅使用已有本地 provider 配置；见 [真实模型说明](docs/phase25_acceptance.md)。

## 测试与评估

```powershell
python -m pytest -q tests/test_file_workflow.py tests/test_desktop_foundation.py tests/test_desktop_reporting.py tests/test_grounded_renderer.py -p no:cacheprovider --basetemp .pytest-phase4
```

当前确定性结果：**34 passed，1 skipped**。评估集为 [evaluation_tasks.json](evaluation/evaluation_tasks.json)，含 25 条无敏感任务。真实 LLM 评估尚待本机 provider 配置后补跑；未填写 Citation Validity、结构化解析成功率或端到端成功率。

更多阶段证据：[Phase 2](docs/phase2_acceptance.md)、[Phase 2.5](docs/phase25_acceptance.md)、[Phase 3](docs/phase3_acceptance.md)。
