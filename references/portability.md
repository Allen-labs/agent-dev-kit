# 可携带环境：Agent Dotfiles 模式

根因：项目配置（AGENTS.md / .agents/）随仓库走，本来不丢；真正丢的是**个人 agent 环境**——好 skill、MCP、个人偏好、定制流程，它们存在每个工具各自的目录里（Claude Code `~/.claude/`、Cursor `~/.cursor/`、WorkBuddy `~/.workbuddy/`、Codex `~/.codex/`）。换工具 = 这套个人环境全没了。

解法 = 给个人环境也建一个"单一真相源 + 适配器"（Agent Dotfiles 模式）。

## 配置类型与丢失风险

| 配置类型 | 存哪 | 换工具丢不丢 |
|---|---|---|
| 项目规范/流程 | 仓库内 AGENTS.md + .agents/ | 不丢（随仓库走） |
| 个人 skill | 各工具 `~/.xxx/skills/` | **丢** |
| 个人 MCP | 各工具 `~/.xxx/mcp.json` / config.toml | **丢** |
| 个人偏好/定制流 | 各工具私有格式 | **丢** |

## 成熟工具（不用从零造）

- **AgentDock（spsz831）**：CLI "给 AI 编程助手做 dotfiles"——`scan`（提取 MCP/Skill/Agent/Plugin/Hook，密钥隔离进 .env）→ `export`（打包可迁移）→ `install`（安全还原，dry-run/越界校验/原子写/幂等）→ `doctor`（健康度/可迁移性/是否泄密）→ `diff`/`uninstall`。
- **agent-dotfiles（npm, Saqib）**："写一次规则，同步到每个 agent"。`sync rules --from AGENTS.md --to all`、`sync skills --from .claude/skills --to all`；智能跳过已原生读取源文件的工具；支持 skip/overwrite/merge 与 copy/symlink。

两者互补：AgentDock 偏"备份/版本/迁移整个环境"；agent-dotfiles 偏"规则/技能跨 agent 传播"。

## MCP 跨工具其实很简单

底层 MCP server 定义三工具通用，只是包裹格式不同：

| 工具 | MCP 配置位置 / 格式 |
|---|---|
| Cursor / Claude Code | `mcpServers` JSON（.cursor/mcp.json / .mcp.json） |
| Codex CLI | TOML `[mcp_servers.*]`（~/.codex/config.toml） |
| Zed | `context_servers` |
| OpenCode | 顶层 `mcp` |
| VS Code / Gemini | `servers` / ~/.gemini/settings.json |
| **WorkBuddy** | **~/.workbuddy/mcp.json** |

→ "迁移 MCP" = 把同一份 server 定义翻译成目标格式（见 `tool-adapters.md`）。**密钥一律隔离进 `.env`，绝不进仓库。**

## canonical 仓库形态

```
<canonical-repo>/                # git 仓库 · 唯一真相源
├── AGENTS.md                    # 共享规范/流程（canonical）
├── flow.md                      # 个性化研发流程
├── user.md                      # 个人偏好
├── skills/                      # 好 skill 沉淀（含本 agent-dev-kit）
├── mcp/mcp.servers.json         # 工具无关的标准 MCP 定义（env 占位）
├── adapters/                    # 目标工具薄适配器模板
├── .agents/                     # 可随仓库走的记忆/会话系统
└── .env.example                 # 密钥占位（真实 .env 不进仓库）
```

换工具 = 克隆仓库 → `bootstrap.py --tool <目标>` → 1 分钟复原。

## "agent 适配优化"诉求怎么落地

你要的不只是搬运，而是让 Agent 把最优配置**适配/优化**到新工具：
1. 读 canonical 配置（AGENTS.md / flow.md / skills / MCP）
2. 读目标工具的能力画像（原生读什么文件、skill 格式、MCP 怎么配、能力缺口）
3. Agent 产出适配版：把工具专属 skill 改写成目标工具等价物；跑不起来的 MCP 标记/替换；按目标工具惯例重排规范
4. 这正是 `agent-folder-init --platform` 的思路 + 本技能的适配层
