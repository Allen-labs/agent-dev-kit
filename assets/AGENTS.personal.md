# Personal Developer Constitution

> 跨项目、跨工具的**通用**开发准则（唯一真相源 / canonical）。
> 由 `agent-dev-kit` 的 `migrate` 模式生成，通过各工具薄适配器扇出：
> WorkBuddy `AGENTS.md` / Claude `CLAUDE.md` / Gemini `GEMINI.md` / Cursor `.cursorrules`+`.mdc`
> / Codex `AGENTS.md` / OpenCode `opencode.json` / Zed `settings.json`。改这里一次，所有工具同步。
> 这是**个人级**宪法；**项目级**的具体命令 / 禁区请看各仓库根 `AGENTS.md`。

## 通用工程原则（对我做任何项目都成立）
- **先读后动**：动手前先读本文件、`flow.md` 与项目级 `AGENTS.md` / `.agents/memory/*`。
- **小步提交、频繁集成**：每次提交只做一件事，能独立 revert。
- **测试先行（TDD）**：非平凡功能先写失败测试再写实现；修 bug 先写复现测试。小型变更（单行修复 / 配置）走快路径，可跳过测试脚手架（见 `flow.md`）。
- **能用确定性工具校验的，不写进自然语言规则**：lint / typecheck / 单测交给工具，本文件只写"必须跑 + 必须全绿"。
- **不手改生成物**：`generated/`、`dist/`、`*.pb.go`、`package-lock.json` 等由工具产出，改动回到源头。
- **少即是多**：本文件控制在 150 行内；细节下沉到 `.agents/memory/*`。

## 工具与栈偏好
- 包管理：按项目（pnpm / npm / uv / cargo / go mod），不跨项目强推。
- 分支策略：`main` 受保护；功能走 `feature/*`，合并用 **squash** 保持线性历史。
- 提交风格：**Conventional Commits** —— `type(scope): subject`，type ∈ {feat,fix,docs,refactor,test,chore}。
- 代码评审：对外 PR 必须过 CI + 至少 1 人 review；AI 改动不跳过人工 review。

## 验证闸门（任何任务"声称完成"前必须全绿）
- 构建：`pnpm build` / `npm run build` / `make build`（按项目）
- 测试：`pnpm test` / `pytest` / `go test ./...`
- 类型与 lint：`tsc --noEmit` / `pre-commit run --all-files`
- → 未全绿，不算完成；不得请求 review。

## 禁区（任何工具 / agent 都不得违反）
- 绝不提交密钥、`.env`、凭据文件；密钥只走环境变量 / 密钥管理器。
- 绝不 `git push --force` 到受保护分支；force push 仅限私有临时分支且需显式确认。
- 绝不手改 `generated/` 产物；改动必须回到生成源。
- 绝不对生产库做写操作（DROP / DELETE / migrate）除非带回滚脚本且经确认。

## 个性化研发流程
详见 `flow.md`（由 `migrate` 一并生成，并对接 WorkBuddy 内置 skill：
writing-plans / executing-plans / subagent-driven-development /
test-driven-development / verification-before-completion / requesting-code-review）。

## 支撑能力（MCP / hooks，详见 `mcp/README.md` 与 `hooks/`）
- MCP：Context7（实时文档）、Filesystem、Memory、Playwright、GitHub、Postgres、SQLite。
- Hooks：提交前密钥扫描、危险命令确认、任务结束记忆回写。

## Reference（本仓库导航）
| 路径 | 内容 |
| `skills/` | 沉淀的好 skill（随工具扇出） |
| `mcp/mcp.servers.json` | 我的 MCP server（密钥走 `.env`，不进仓库） |
| `flow.md` | 我的研发流程 |
| `user.md` | 我的个人偏好 |
| `hooks/` | 自动化护栏脚本（密钥扫描 / 危险命令 / 记忆回写） |
| `adapters/` | 各工具薄适配器模板 |
