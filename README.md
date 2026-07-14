# MewCode 项目审查材料

> 本仓库用于评估一个已有 Python Coding Agent 项目的技术结构与后续个人迭代方向，不作为“从零原创”的项目展示。

## 项目来源与当前状态

- 本仓库包含已有的 MewCode Python 源码；代码文件中保留了原有来源标注。
- 当前阶段的目标是理解其架构，并在后续围绕具体场景完成独立改造、评测与文档沉淀。
- 本仓库暂不作为最终简历项目；简历只会描述本人实际完成、验证并能独立讲解的改造。

## 当前已有能力

- 终端交互式 Coding Agent 与远程 Web 模式
- Anthropic / OpenAI 协议模型接入
- MCP 工具扩展与动态工具加载
- Skills 加载与执行
- 文件读写、终端命令、代码编辑等工具调用
- 上下文压缩、会话持久化与自动记忆
- 权限控制、危险命令检测、路径沙箱与 Worktree 隔离
- 子 Agent / Team 协作及任务消息传递
- 单元测试覆盖 Agent 循环、上下文、权限、MCP、记忆与协作模块

## 希望评估的问题

1. 该项目是否值得作为 Agent 求职项目的代码底座继续投入？
2. 更适合迭代为开发者 Coding Agent、个人求职桌面 Agent，还是其他方向？
3. 如果继续迭代，哪些核心能力最值得由本人独立完成并形成可验证的评测？

## 本地运行

需要 Python 3.11+。复制配置模板并填入自己的模型服务凭据：

```powershell
Copy-Item .mewcode/config.yaml.example .mewcode/config.yaml
```

随后按 `pyproject.toml` 安装依赖，并运行：

```powershell
python -m mewcode
```

请勿提交 `.mewcode/config.yaml`、API Key、会话日志或其他本地凭据。
