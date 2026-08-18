---
name: agent-dev-kit
description: 融合"项目宪法生成、个性化研发流程、可携带环境迁移"的统一套件。当用户需要以下任意场景时务必使用：① 从零初始化一个对 AI Agent 友好的开发环境（生成 AGENTS.md 项目宪法 + .agents/ 记忆与会话结构）；② 把项目规范要求、个性化开发流程固化成 Agent 可稳定读取执行的明文（flow.md）；③ 在不同 AI 编码工具（WorkBuddy / Claude Code / Cursor / Codex）之间迁移，快速复原并适配最优的 skill 与 MCP 配置；④ 提到"项目规范""AGENTS.md""CLAUDE.md""开发流程管理""skill/MCP 丢失""换工具迁移""agent dotfiles"等关键词时。即使他们没有显式说"帮我建环境"，只要涉及 Agent 辅助开发的规范沉淀与跨工具一致性，也应触发本技能。
---

# agent-dev-kit

把"用 Agent 做开发"需要的三种能力融合成一个可复用的套件，三者共享同一份 **canonical（唯一真相源）**，互不重复、可扇出、可迁移：

| 模块 | 解决什么 | 来自哪 |
|---|---|---|
| ① Constitution（项目宪法） | 生成高质量 `AGENTS.md` + 脚手架 `.agents/` 结构 | `writing-a-good-agents-md`（方法论）+ `agent-folder-init`（脚手架） |
| ② Workflow（个性化流程） | 把定制研发流程固化成 `flow.md`，对接 WorkBuddy 内置 skill | 本工作区已有的 spec-driven / writing-plans / subagent-driven / tdd / verification / code-review 等 |
| ③ Portability（可携带环境） | 扫描当前环境 → 导出 canonical → 装到新工具并适配 → 体检 | Agent Dotfiles 模式 + AgentDock / agent-dotfiles 思路 |

核心纪律：**单一真相源 + 薄适配器**。项目规范、流程、skill、MCP 只在一处维护（canonical 仓库），每个工具/项目只放一个指向它的薄文件，杜绝三份拷贝漂移（过时的规则比没有更危险）。

## 三模式路由

进入本技能后，先判断用户意图属于哪个模式，再走对应分支。一个任务常会串联多个模式（例如先 init 建规范，再 migrate 带走）。

### 模式 A · init（项目宪法）
目标：为某个仓库生成 `AGENTS.md` + `.agents/` 结构。
1. 读 `references/agents-md-principles.md` —— 6 条原则 + 审计清单（保证质量）。
2. 读 `references/folder-structure.md` —— `.agents/` 目录布局与每文件职责。
3. 用 `scripts/scaffold.py`（默认 dry-run，加 `--write` 才落盘；拒绝越界、拒绝覆盖、拒绝 symlink、模板缺失即硬失败，绝不退而求其次）。`AGENTS.md` 模板统一从 `assets/AGENTS.md.template` 单一来源读取。
4. 用 `assets/AGENTS.md.template` 作骨架，向用户补齐：技术栈、目录/入口、构建/测试/登录真实命令、禁区、Git 规范。
5. 生成 `flow.md`（模式 B 的初稿）。
6. 用 `references/agents-md-principles.md` 的审计清单自检一次，再交付。

### 模式 B · flow（个性化研发流程）
目标：把用户的开发节奏与特殊要求写成 Agent 可执行的 `flow.md`。
1. 读 `references/flow-template.md` —— 固定节奏 / 角色分工 / 个性化约定三块模板。
2. 读 `references/workbuddy-skills-map.md` —— 把每类流程动作映射到 WorkBuddy 内置 skill（spec-driven-development、writing-plans、planning-and-task-breakdown、subagent-driven-development、using-git-worktrees、tdd、verification-before-completion、code-review、finishing-a-development-branch）。
3. `flow.md` 就是这些内置 skill 的"调用说明书"，写明本项目走哪几步、谁先谁后、什么不过不合并。
4. 把高频动作沉淀为项目级 Slash Command / 子技能（如"按规范生成单测"）。

### 模式 C · migrate（可携带环境迁移）
目标：换工具时快速复原并适配最优配置。完整命令链（均已实测）：
1. `scripts/scan_env.py --materialize <canonical目录>` —— 扫描当前 WorkBuddy 环境的 skills + mcp.json，materialize 成 canonical 仓库骨架：`skills/`（复制，排除子仓库 `.git` 避免 gitlink 空洞）、`mcp/mcp.servers.json`（密钥全部替换为 `${ENV}` 占位，绝不写死）、`flow.md`、`user.md`、`adapters/`、`AGENTS.md`（个人级宪法）。也可只用 `--out report.json` 仅打印报告。
   - 技能内置一份 **MCP 最佳集合**模板（`assets/mcp/mcp.servers.json` + `mcp/README.md`：Context7 / Filesystem / Memory / Playwright / GitHub / Postgres / SQLite，2026 验证的官方/厂商包名）与 **hooks 护栏**（`assets/hooks/`：密钥扫描 / 危险命令确认 / 记忆回写 3 个跨平台脚本 + `hooks.json` 声明）。把它们合并进你的 canonical，即得"最好一套"配置。
2. `references/tool-adapters.md` —— 按目标工具（workbuddy / claude / cursor / codex / **opencode** / **zed**）的薄适配器说明 + MCP 格式翻译规则（JSON / TOML / OpenCode `mcp` / Zed `context_servers`）+ Hooks 接线方式。
3. `scripts/bootstrap.py --canonical <目录> --tool <目标>` —— 把 canonical 扇出（copy）到目标工具目录；写入前**自动备份**已有 `mcp.json` 为 `.bak`；canonical 含 `adapters/` 或 `hooks/` 时一并复制。**默认 dry-run，加 `--write` 才落盘；`--force` 覆盖已有文件**。**警告：写到真实 home 目录（如 `~/.workbuddy`）会改动你现有环境，务必先 dry-run 确认，且本技能绝不主动对真实目录 `--write`——由你显式决定。**
4. `scripts/doctor.py --canonical <目录>` —— 体检：AGENTS.md 质量 / 泄密扫描（已排除 `${{ secrets.X }}` 等模板变量与文档示例误报）/ 必需文件 / 与 canonical 的 drift。

## 何时读什么（渐进披露）

SKILL.md 只给地图，细节按需读 `references/`：
- 写/审 AGENTS.md → `agents-md-principles.md`
- 建 `.agents/` 结构 → `folder-structure.md`
- 写流程 → `flow-template.md` + `workbuddy-skills-map.md`
- 跨工具迁移 → `portability.md` + `tool-adapters.md`

脚本只在需要做确定性动作（建结构、扫描、扇出、体检）时执行，不在纯讨论时跑。

## 安全与纪律

- 永远把自动生成的初稿当草稿重写 —— 手写而非自动生成。
- 密钥只进 `.env` / 环境变量，绝不进 canonical 仓库或 AGENTS.md。
- 脚手架脚本：默认 dry-run；写入须显式 `--write`；不越界写 cwd 之外；不覆盖已有入口文件（除非 `--force`）；不解析 symlink；模板缺失即失败、不留半成品。
- 规范文件保持精简（AGENTS.md < 150 行），它是"活的文档"，随工作流变更就审。
- 理解 Agent 为何会跳过指令：每条规则必须"有用且具体"，否则 Agent 会判断无关而忽略。

## 交付物清单（一次完整 init + migrate 后）

```
<canonical-repo>/            # git 仓库 · 唯一真相源
├── AGENTS.md                # 项目宪法
├── flow.md                  # 个性化研发流程
├── user.md                  # 个人偏好
├── skills/                  # 好 skill 沉淀
├── mcp/mcp.servers.json     # 工具无关的 MCP 标准定义（env 占位）
├── mcp/README.md            # 每个 server 用途/依赖/安全要点
├── hooks/                   # 自动化护栏脚本（密钥扫描/危险命令/记忆回写）
├── .agents/                 # 可随仓库走的记忆/会话系统
│   ├── README.md
│   ├── memory/  (architecture / conventions / deployment / data-model / tech-debt / flow)
│   └── sessions/
├── adapters/                # 目标工具薄适配器
│   ├── workbuddy.md
│   ├── claude.md
│   ├── cursor.md
│   └── codex.md
└── .env.example             # 密钥占位（真实 .env 不进仓库）
```
