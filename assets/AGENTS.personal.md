# Personal Developer Constitution

> 跨项目、跨工具的**通用**开发准则。由 `agent-dev-kit` 的 `migrate` 模式生成，
> 作为唯一真相源（canonical），通过各工具的薄适配器（CLAUDE.md / GEMINI.md /
> `.cursorrules` / `.mdc`）扇出。改这里一次，所有工具同步。

## 通用原则（对“我做任何项目”都成立）
- [你的通用编码原则，如：小步提交、测试先行、不动手改生成物]
- [如：先读 AGENTS.md / flow.md 再动手]
- [如：能用确定性工具（lint/typecheck）校验的，不写进自然语言规则]

## 工具与栈偏好
- 包管理：[pnpm / npm / uv / cargo ...]
- 编辑器 / IDE：[...]
- 默认分支策略：[main + squash merge / rebase ...]
- 提交风格：[ Conventional Commits: `type: subject` ]

## 禁区（任何工具 / agent 都不得违反）
- 绝不提交密钥或 `.env`
- 绝不手改 `generated/` 产物
- [你的其他硬性红线]

## 个性化研发流程
详见 `flow.md`（由 `migrate` 一并生成，并对接 WorkBuddy 内置 skill）。

## Reference（本仓库导航）
| 路径 | 内容 |
| `skills/` | 我沉淀的好 skill（随工具扇出） |
| `mcp/mcp.servers.json` | 我的 MCP server（密钥走 `.env`，不进仓库） |
| `flow.md` | 我的研发流程 |
| `user.md` | 我的个人偏好 |
| `adapters/` | 各工具薄适配器模板 |
