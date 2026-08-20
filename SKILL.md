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

所有命令默认 dry-run（只打印计划），加 `--write` 才落盘。加 `--json` 输出结构化数据供 agent 消费。

## agent 操作手册（何时调什么）

### 场景 1：用户第一次建环境
```
1. agent 调: python agent-kit.py init ~/agent-dotfiles
2. agent 读生成的 AGENTS.md / flow.md，和用户确认规范
3. agent 调: python agent-kit.py check --canonical ~/agent-dotfiles  # 检查
4. 确认无误后: python agent-kit.py apply --canonical ~/agent-dotfiles --tool workbuddy --write
```

### 场景 2：换到 Claude Code
```
1. agent 调: python agent-kit.py backup --tool claude              # 先备份现有配置
2. agent 调: python agent-kit.py apply --canonical ~/agent-dotfiles --tool claude (dry-run)
3. agent review 计划（推哪些 skill、MCP 怎么翻译、CLAUDE.md 会不会覆盖已有）
4. 用户确认后: --write 落盘
5. agent 调: python agent-kit.py check --canonical ~/agent-dotfiles --tool claude  # 确认同步
```

### 场景 3：用户在 WorkBuddy 装了新 skill
```
1. agent 调: python agent-kit.py collect --canonical ~/agent-dotfiles --tool workbuddy (dry-run)
2. agent review 回灌清单（哪些是真好 skill、哪些是临时试验）
3. 确认后 --write
4. agent 调: python agent-kit.py apply --canonical ~/agent-dotfiles --tool claude --write  # 同步到其他工具
```

### 场景 4：改了 canonical 里的 skill
```
1. agent 调: python agent-kit.py check --canonical ~/agent-dotfiles  # 确认没改坏
2. agent 调: python agent-kit.py apply --canonical ~/agent-dotfiles --tool all --write  # 推到所有工具
3. agent 调: python agent-kit.py check --canonical ~/agent-dotfiles --tool workbuddy  # 确认 synced
```

### 场景 5：已配置过，想覆盖升级
```
1. agent 调: python agent-kit.py apply --canonical ~/agent-dotfiles --tool claude --upgrade (dry-run)
   # upgrade 模式会自动先 backup，再覆盖 canonical 管理的已变更文件，不动你自己在工具里新增的 skill
2. agent review 计划（哪些是 modified、backup 在哪）
3. 用户确认后: --write 落盘
4. 如需回滚: 从 plan["backed_up"] 路径恢复
```

## 命令输出解读

脚本输出 `--json` 时，agent 应关注：
- `backup`: `data.files` = 备份了哪些文件、`data.path` = 备份在哪
- `apply`: `data.summary` = "N new, M modified, K skipped"——判断是否需要重推；`data.backed_up` = upgrade 模式的备份路径（回滚用）
- `collect`: `data.collected` = 回灌了哪些 skill——决定是否要 review
- `check`: `data.overall` = "ok" 才能安全 apply；`data.drift.drifted` > 0 说明该工具不一致

## 地基资产分发（apply 时自动做）

- `commands/` → `.claude/commands/`、`.cursor/commands/`、`.codex/prompts/`（斜杠命令开箱即用：commit/review/test）
- `rules/` → `.cursor/rules/*.mdc`（作用域规则的 `scope` 翻译为 `globs`；`global.mdc` 始终指向 AGENTS.md，替代 legacy `.cursorrules`）
- `spec-templates/` → 项目 `.agents/spec-templates/`（由 scaffold 分发，供 `specs/<feature>/` 落盘）

## 三模式路由（项目宪法 / 个性化流程 / 迁移）

五命令覆盖迁移全生命周期。项目宪法和流程的生成仍用原模式：

### 模式 A · init（项目宪法）
1. 读 `references/agents-md-principles.md` —— 6 条原则 + 审计清单。
2. 读 `references/folder-structure.md` —— `.agents/` 目录布局。
3. 用 `scripts/scaffold.py`（默认 dry-run，`--write` 才落盘）。模板从 `assets/AGENTS.md.template` 单一来源读取。
4. 用模板作骨架，向用户补齐：技术栈、构建/测试命令、禁区、Git 规范。
5. 生成 `flow.md`（模式 B 初稿），用审计清单自检后交付。

### 模式 B · flow（个性化研发流程）
1. 读 `references/flow-template.md` + `references/workbuddy-skills-map.md`。
2. `flow.md` 是 WorkBuddy 内置 skill 的"调用说明书"，写明本项目走哪几步。
3. 流程按任务规模分级：小型变更走快路径，非平凡功能走完整 Pipeline。

### 模式 C · migrate（可携带环境迁移）
完全由五命令覆盖（见上方"agent 操作手册"）。`agent-kit.py init` 从当前环境快照生成 canonical。

> 注：`bootstrap.py` / `doctor.py` / `scan_env.py` 已删除（功能合并进 `agent-kit.py`，git 历史可恢复）。统一用 `agent-kit.py`。

## 何时读什么（渐进披露）

- 写/审 AGENTS.md → `references/agents-md-principles.md`
- 建 `.agents/` 结构 → `references/folder-structure.md`
- 写流程 → `references/flow-template.md` + `references/workbuddy-skills-map.md`
- 跨工具迁移格式 → `references/tool-adapters.md`
- 架构演进历史（一般不需要读）→ `references/architecture-upgrade-design.md`

脚本只在需要做确定性动作时执行，不在纯讨论时跑。

## 安全与纪律

- 密钥只进 `.env`（canonical 根目录，gitignore），绝不进仓库或 AGENTS.md。
- `apply` 时从 `.env` 注入真实密钥到目标工具配置；canonical 里的 `mcp.servers.json` 永远保留 `${}` 占位。
- 脚手架脚本：默认 dry-run；写入须显式 `--write`；不越界写 cwd 之外；不覆盖已有文件（除非 `--force`）。
- AGENTS.md < 150 行；每条规则必须"有用且具体"，否则 agent 会判断无关而忽略。
- **apply 到真实 home 目录会改动现有环境**——务必先 dry-run 确认，agent 绝不主动对真实目录 `--write`。

## canonical 同步约定（踩坑固化）

**往已存在的目录同步（如把 skill 开发版同步进 canonical）时，禁止直接 `cp -r src dst`**——
POSIX 语义下 dst 已存在会生成 `dst/src/` 嵌套，且顶层文件不会被更新。
正确做法（三选一）：

```bash
# ① 先删目标再拷（最常用）
rm -rf dst && cp -r src dst
# ② rsync 同步（推荐，--delete 可清理目标多余文件）
rsync -a --delete src/ dst/
# ③ 沙箱环境用 python（os 层删除，绕开回收站钩子）
shutil.copytree(src, dst, dirs_exist_ok=True)
```

同步后必须验证：`grep` 新函数名 / 新文件存在 / `git status` 干净——防止"拷了但没更新"的静默失败。

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
├── .sync/manifest.json         # 同步状态（SHA256，运行时生成）
├── .env                        # 密钥（gitignore，不入仓库）
└── .env.example                # 密钥占位模板（入仓库）
```
