---
name: agent-dev-kit
description: 融合"项目宪法生成、个性化研发流程、可携带环境迁移"的统一套件。当用户需要以下任意场景时务必使用：① 从零初始化一个对 AI Agent 友好的开发环境（生成 AGENTS.md 项目宪法 + .agents/ 记忆与会话结构）；② 把项目规范要求、个性化开发流程固化成 Agent 可稳定读取执行的明文（flow.md）；③ 在不同 AI 编码工具（WorkBuddy / Claude Code / Cursor / Codex / OpenCode / Zed）之间迁移，快速复原并适配最优的 skill 与 MCP 配置；④ 提到"项目规范""AGENTS.md""CLAUDE.md""开发流程管理""skill/MCP 丢失""换工具迁移""agent dotfiles"等关键词时。即使他们没有显式说"帮我建环境"，只要涉及 Agent 辅助开发的规范沉淀与跨工具一致性，也应触发本技能。
---

# agent-dev-kit

把"用 Agent 做开发"需要的规范、流程、skill、MCP 融合成一个**可携带的 canonical 仓库**，用五个命令管理全生命周期。

## 核心理念

**脚本与 agent 互相依托**：
- 脚本是 agent 的手脚——做 agent 做不了的事（文件操作、checksum、格式翻译、密钥注入）
- agent 是脚本的指挥——判断何时 apply、review collect 回来的 skill、决定升级策略
- 脚本输出 JSON（`--json`），agent 直接消费做决策；SKILL.md 是 agent 的操作手册

**单一真相源 + 薄适配器**：规范、流程、skill、MCP 只在 canonical 仓库维护一处，每个工具只放薄指令文件指向它。

## 五命令生命周期

```
init → backup → apply → [日常: collect / check] → [改 canonical 后: check → apply]
```

| 命令 | 做什么 | agent 何时调 |
|---|---|---|
| `init <path>` | 初始化：从当前 WorkBuddy 快照生成 canonical 仓库 | 用户说"初始化/建环境/把当前配置带走" |
| `backup --tool <t>` | 备份：把目标工具的现有配置备份到安全目录 | apply 前先备份，用户说"先备份一下" |
| `apply --tool <t>` | 应用：把 canonical 配置应用到目标工具（幂等 SHA256 + .env 注入） | 用户说"装到 Claude/Cursor/Codex"或"扇出" |
| `apply --tool <t> --upgrade` | 升级：先自动 backup 再覆盖 canonical 管理的已变更文件，**不动**工具里用户自己新增的 skill | 用户说"已配置过，想覆盖升级"或"更新到最新版" |
| `collect --tool <t>` | 收集：把工具新装的 skill 回灌到 canonical | 用户说"我在 workbuddy 装了新 skill"或"回灌" |
| `check [--tool]` | 检查：体检 canonical（质量+泄密+skill引用）；`--tool` 时附带 drift 检测 | 改了 canonical 后、apply 前、日常巡检 |
| `sync --src <dev> --skill <n>` | 同步：把开发版 skill 干净同步到 canonical（先删再拷，沙箱兼容） | 改完 agent-dev-kit 代码后 |

所有命令默认 dry-run（只打印计划），加 `--write` 才落盘。加 `--json` 输出结构化数据供 agent 消费。全部支持 `--tool all`。

## agent 操作手册

通用流程：**dry-run → review → --write → check**。场景差异：

| 场景 | 关键命令 | 注意 |
|---|---|---|
| 首次建环境 | `init` → `check` → `apply --tool all --write` | init 后填 `.env` 密钥 |
| 换到新工具 | `backup --tool <t>` → `apply --tool <t>` (dry-run) → `--write` | review MCP 翻译是否覆盖已有 |
| 装了新 skill | `collect --tool workbuddy` (dry-run) → `--write` → `apply --tool all` | review 回灌清单 |
| 改了 canonical | `check` → `apply --tool all --write` → `check --tool all` | 确认全绿 |
| 覆盖升级 | `apply --tool <t> --upgrade` (dry-run) → `--write` | upgrade 自动 backup，不动用户新增 |
| 新机器复原 | `init <path> --from <git-url>` → `apply --tool all --write` | 从 GitHub clone canonical |

## 命令输出解读

- `apply`: `data.summary` = "N new, M modified, K skipped"；`data.backed_up` = 回滚路径
- `collect`: `data.collected` / `data.updated` = 回灌了什么
- `check`: `data.overall` = "ok" 才能安全 apply；`data.drift.drifted` > 0 说明不一致

## 地基资产分发（apply 时自动做）

- `commands/` → `.claude/commands/`、`.cursor/commands/`、`.codex/prompts/`（斜杠命令开箱即用：commit/review/test）
- `rules/` → `.cursor/rules/*.mdc`（作用域规则的 `scope` 翻译为 `globs`；`global.mdc` 始终指向 AGENTS.md，替代 legacy `.cursorrules`）
- `agents/` → `.claude/agents/`（通用子代理：code-reviewer / verification-runner；方法论归 `subagent-driven-development` skill）
- `spec-templates/` → 项目 `.agents/spec-templates/`（由 scaffold 分发，供 `specs/<feature>/` 落盘）

## 项目宪法与流程生成

五命令覆盖迁移。项目宪法和流程的生成用 `scaffold.py`：

- **AGENTS.md**：读 `references/agents-md-principles.md`（6 原则 + 审计清单），用 `assets/AGENTS.md.template` 骨架，向用户补齐技术栈/命令/禁区/Git 规范。
- **flow.md**：读 `references/flow-template.md` + `workbuddy-skills-map.md`，按任务规模分级（小变更快路径 / 完整 Pipeline）。
- **`.agents/` 结构**：读 `references/folder-structure.md`。

> `bootstrap.py` / `doctor.py` / `scan_env.py` 已删除，统一用 `agent-kit.py`。

## 何时读什么（渐进披露）

- 写/审 AGENTS.md → `references/agents-md-principles.md`
- 建 `.agents/` 结构 → `references/folder-structure.md`
- 写流程 → `references/flow-template.md` + `references/workbuddy-skills-map.md`
- 跨工具迁移格式 → `references/tool-adapters.md`
- 架构演进历史（一般不需要读）→ `references/architecture-upgrade-design.md`

脚本只在需要做确定性动作时执行，不在纯讨论时跑。

## 安全与纪律

- 密钥只进 `.env`（gitignore），`apply` 时注入；canonical 里永远 `${}` 占位。
- 默认 dry-run；`--write` 才落盘；不越界写 cwd 之外。
- AGENTS.md < 150 行；每条规则"有用且具体"。
- **apply 到真实 home 会改现有环境**——先 dry-run，agent 绝不主动 `--write`。
- canonical 同步约定见 `references/sync-conventions.md`（给开发者，非 agent）。

## 交付物清单

```
<canonical-repo>/                # git 仓库 · 唯一真相源
├── AGENTS.md                   # 项目宪法（<150 行）
├── flow.md                     # 个性化研发流程（按任务规模分级）
├── user.md                     # 个人偏好
├── skills/                     # 常驻 skill（30+ 个核心，以实际为准）
├── skills-optional/            # 按需 skill（18 个文档/资产类）
├── mcp/mcp.servers.json        # MCP 定义（${} 占位，安全）
├── mcp/README.md               # MCP 选型说明
├── hooks/                      # 自动化护栏（secret_scan / danger_confirm / memory_update）
├── adapters/                   # 各工具薄适配器模板
├── commands/                   # 斜杠命令资产（commit/review/test，apply 分发）
├── rules/                      # 作用域规则资产（frontmatter 声明 scope，极简）
├── spec-templates/             # spec/plan 工作流模板（scaffold 分发给项目）
├── agents/                     # 通用子代理资产（code-reviewer/verification-runner）
├── .sync/manifest.json         # 同步状态（SHA256，运行时生成）
├── .env                        # 密钥（gitignore，不入仓库）
└── .env.example                # 密钥占位模板（入仓库）
```
