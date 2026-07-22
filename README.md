# LocalDesk Agent

面向用户**明确授权本地目录**的受控 Desktop Agent：检索本地资料、生成带引用的 Markdown/DOCX 草稿、经确认后交付；也能在独立确认后对 `managed_roots` 执行确定性文件整理，并通过另一份独立确认的 Task 回滚。

## 来源与独立改造范围

本仓库基于 MewCode Python Coding Agent 学习型底座改造。原始代码及来源标注保留，不宣称从零开发。本人独立完成的 LocalDesk 改造集中在 `localdesk/desktop/`：任务状态机、路径授权、deny-first Policy Guard、Trace、资料检索、staging/哈希确认交付、Grounded LLM 渲染约束、文件整理与回滚核心工作流、测试与文档。

## 架构

```text
用户任务
  -> Knowledge Skill（仅 read_roots，返回 citation_id）
  -> Deterministic / Grounded LLM Renderer（只接收检索片段）
  -> Document Skill（task staging + SHA-256）
  -> Policy Guard + 独立确认
  -> output_root 交付 + task Trace

managed_roots -> FileOrganizationWorkflow（dry-run + 哈希预览 -> 独立确认 -> journal -> 独立确认 rollback）
```

## 安全模型

| 目录 | 权限 |
|---|---|
| `read_roots` | 仅检索资料 |
| `managed_roots` | 仅确定性整理流程在独立确认后 move；禁止删除、覆盖和越权 |
| `output_root` | 仅确认后交付 Markdown / DOCX |
| `task_root` | task.json、events.jsonl、staging、operation journal |

越权、覆盖、删除、Shell、网络操作直接拒绝。所有写入先 staging；确认前 output 零副作用，确认时复核草稿 SHA-256。每个任务有 task_id、计划、策略决定、确认和产物 Trace。

## 当前能力与非目标

- 支持 MD/TXT/可提取文本 PDF 的轻量检索，引用定位到行号或页码。
- 支持确定性带引用 Markdown 草稿和确认交付。
- 支持 Grounded LLM JSON 渲染：每段必须给出本次检索内真实 citation_id；幻觉引用、无引用、解析失败、超时均拒绝暂存。
- 支持受控文件整理 CLI：dry-run 预览、执行前 SHA-256 复核、确认后的串行 move、operation journal、独立确认 rollback；详见 [Phase 4](docs/phase4_file_organization.md)。
- 支持仅面向白名单测试窗口的 Windows UIA Demo：确认后输入构造文本、调用低风险按钮、验证窗口状态；UIA 不稳定时停止并人工接管，详见 [Phase 5](docs/phase5_desktop_computer_use.md)。
- 当前网页能力是“受控网页读取”，不是完整 Browser Agent；尚无搜索或链接发现能力。
- 不支持：任意 Shell、删除、覆盖、完整 Browser Agent、MCP、多 Agent、Electron、真实 GUI 自动化、扫描件 OCR。

## 无敏感报告 Demo

创建仅含构造资料的目录，按 [历史报告 Demo](docs/archive/v1/report_demo.md) 执行两步：第一次仅 staging，第二次携带 task_id 才交付。真实模型需额外加 `--desktop-grounded-llm`，且仅使用已有本地 provider 配置；见[历史真实模型说明](docs/archive/v1/phase25_acceptance.md)。

## 测试与评估

```powershell
python evaluation/run_phase4_evaluation.py
```

当前 Phase 4 确定性结果：**45 passed，1 skipped**。评测任务集为 [phase4_tasks.json](evaluation/phase4_tasks.json)，覆盖 5 类无敏感文件整理场景；真实结果见 [phase4_file_organization.json](evaluation/results/phase4_file_organization.json)。跳过项是当前 Windows 账户无法创建真实 symlink；mock 注入的拒绝路径已经通过。真实 LLM 评估仍待本机 provider 配置后补跑，尚未声称 Citation Validity、结构化解析成功率或端到端成功率。

当前重构阶段证据见 [文档入口](docs/README.md)；旧项目材料位于 [v1 历史归档](docs/archive/v1/README.md)，不应与当前能力混用。
