# LocalDesk Office Agent 文档入口

这里是项目的统一入口。历史 v1 文档保留为代码与测试证据；当前 Office Agent 重构的状态以 `计划.md` 和 Phase 0 以后文档为准。

建议阅读顺序：先看“项目总览”和“根目录总计划”，再按当前阶段阅读；需要追溯既有能力时再查看历史验收报告。

| 文档 | 用途 |
|---|---|
| [项目总览](项目总览.md) | 当前是否完成、总计划、阶段进展、大白话说明、简历文案 |
| [根目录总计划](../计划.md) | 完整架构、参考项目取舍与原始实施计划 |
| [Phase 0 重建基线](phase0_rebaseline.md) | LocalDesk 重命名后的运行时、核心回归与逐阶段评测起点 |
| [当前架构审计](current_architecture.md) | MewCode 原始底座如何运行、哪些保留/冻结 |
| [重构设计](refactor_plan.md) | LocalDesk 模块边界与安全规则 |
| [基线验证](baseline_validation.md) | 原底座测试环境与已知历史失败 |
| [历史 Phase 1](phase1_foundation.md) | v1 Task/Policy/Trace/Foundation 证据 |
| [历史 Phase 2](phase2_acceptance.md) | v1 引用检索、staging、确认交付证据 |
| [历史 Phase 2.5](phase25_acceptance.md) | v1 Grounded LLM 结构化渲染边界 |
| [历史 Phase 3](phase3_acceptance.md) | v1 文件整理/operation journal/回滚核心模块 |
| [历史 Phase 4](phase4_acceptance.md) | v1 评估、README、Demo、求职材料归档 |
| [报告 Demo](report_demo.md) | 无敏感两步交付演示 |
| [教师查看入口](teacher_review.md) | 一页了解项目能力、证据、边界与待讨论方向 |
| [DeepSeek 真实评估说明](deepseek_real_eval.md) | 不提交 API Key 的本地配置与 5–10 条样例评估方式 |
| [求职材料](job_materials.md) | 简历描述、90 秒介绍、深挖问题 |

评估集位于 [`evaluation/evaluation_tasks.json`](../evaluation/evaluation_tasks.json)。
