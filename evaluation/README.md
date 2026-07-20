# LocalDesk Evaluation

评测分为两层：

1. **回归基线**：`run_baseline.py` 离线运行稳定核心测试，并保存真实结果；它证明已有受控闭环没有回归。
2. **任务评估**：`evaluation_tasks.json` 记录逐阶段扩展的任务场景。只有具备对应可执行 adapter 与验收脚本后，才统计端到端任务成功率、引用有效率等指标。

运行 Phase 0 基线：

```powershell
python evaluation/run_baseline.py
```

默认结果写入 `evaluation/results/phase0_core_baseline.json`。该结果不会声称真实模型、浏览器或 Windows Desktop Computer Use 的效果；这些能力将在对应阶段有可复现脚本后再纳入指标。
