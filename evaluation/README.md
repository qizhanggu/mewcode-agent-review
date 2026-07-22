# LocalDesk Evaluation

评测分为两层：

1. **回归基线**：`run_baseline.py` 离线运行稳定核心测试，并保存真实结果；它证明已有受控闭环没有回归。
2. **任务评估**：`evaluation_tasks.json` 记录逐阶段扩展的任务场景。只有具备对应可执行 adapter 与验收脚本后，才统计端到端任务成功率、引用有效率等指标。

运行 Phase 0 基线：

```powershell
python evaluation/run_baseline.py
```

默认结果写入 `evaluation/results/phase0_core_baseline.json`。该结果不会声称真实模型、浏览器或 Windows Desktop Computer Use 的效果；这些能力将在对应阶段有可复现脚本后再纳入指标。

## Phase 2：受控网页研究与确定性 Reviewer

```powershell
python evaluation/run_phase2_evaluation.py
```

该脚本运行 `tests/test_desktop_foundation.py` 与 `tests/test_desktop_reporting.py`，并将结果写入 `evaluation/results/phase2_controlled_research.json`。它使用 `FakeBrowserAdapter` 和 `httpx.MockTransport` 覆盖白名单、重定向、页面体积、网页脚本文本和 Reviewer 拒绝路径；不访问真实网站，也不把离线测试当作联网任务成功率。

## Phase 3：DOCX 交付与质量门

```powershell
python evaluation/run_phase3_evaluation.py
```

该结果记录 DOCX staging、结构检查、渲染检查编排和双产物交付预检的离线回归。它使用 `FakeDocxRenderer`，因此不会声称真实 PDF/PNG 渲染质量已经验收；真实 LibreOffice 渲染是单独、必须完成的阶段验收门槛。

真实渲染验收（仅使用构造资料）：

```powershell
python evaluation/run_phase3_real_render_demo.py
```

该脚本要求可用的 LibreOffice，实际运行 Markdown → DOCX → PDF → PNG → 确认交付，并保存 Trace、结构与页面数量摘要；它不使用或上传任何真实个人/公司资料。

## Phase 4：受控文件整理与独立回滚

```powershell
python evaluation/run_phase4_evaluation.py
```

该脚本覆盖 `managed_roots` 内的 dry-run、单独确认移动、预览后源文件/目标变化拒绝、失败 journal、独立 rollback Task 和真实 CLI 串联。结果写入 `evaluation/results/phase4_file_organization.json`。测试只创建临时的无敏感样例文件；它不代表项目可以管理任意本机目录。

## Phase 5：Windows UIA 与受限视觉 fallback

```powershell
.\.venv\Scripts\python.exe evaluation\run_phase5_evaluation.py
```

该脚本记录 UIA workflow 的离线回归：窗口白名单、确认绑定、状态变化时停止并人工接管，以及 state-bound fallback。真实验收使用仓库自建的 WinForms 测试窗口和构造文本完成，不访问外部系统；详情见 `docs/phase5_desktop_computer_use.md`。

## Phase 6A：基线冻结、真实 Office Demo 与公网 Trace

```powershell
.\.venv\Scripts\python.exe evaluation\run_phase6a_evaluation.py
.\.venv\Scripts\python.exe evaluation\run_phase6a_demo.py
.\.venv\Scripts\python.exe evaluation\run_real_web_trace.py
```

第一条生成统一离线回归结果；第二条使用构造 JD/履历和真实 LibreOffice 验收求职材料 DOCX；第三条只读访问一个真实公开 HTTPS 页面，并在 Trace 中保存 URL、访问时间、内容哈希、引用片段和发现链接。三类证据分开记录，不能用离线 fake adapter 的通过率代替真实联网或真实渲染结果。
