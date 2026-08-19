# 架构升级设计：从单向复制到双向同步（历史记录）

> **状态**：已完成 · 历史设计文档（2026-08-18 设计 → 2026-08-19 已实现）
> **当前实现**：`agent-kit.py` 五命令（init / backup / apply / collect / check）
> **本文仅作设计演进参考**，操作请一律走 `agent-kit.py`，勿参考已删除的旧脚本

## 一、问题陈述

当前 `agent-dev-kit` 的 `bootstrap.py` 是一个**单向复制生成器**：canonical → 工具目录（copy）。逐行读源码后发现 7 个架构级缺口——不是 bug，是设计范式本身的局限。

### 7 个缺口（附源码行号）

| # | 缺口 | 源码位置 | 后果 |
|---|---|---|---|
| 1 | CLAUDE.md / .cursorrules 计划了但从未写入 | `bootstrap.py:146-147`（plan 有，`--write` 段 161-231 无对应代码） | Claude Code / Cursor 扇出后没有指令文件 |
| 2 | skills 全量复制，非链接 | `bootstrap.py:173-176` `shutil.copytree` | 改 canonical → 6 个工具副本全部 drift |
| 3 | MCP `${ENV}` 占位从未解析 | `translate_mcp():47,59,69` | 工具启动 MCP → env 不存在 → 失败 |
| 4 | 无 `collect` 回灌命令 | 无此功能 | 工具里装新 skill → 无法回灌 canonical |
| 5 | 无 drift 检测 | `doctor.py:111-112`（只打印注释） | 不知道哪个工具和 canonical 不一致 |
| 6 | Codex TOML env 格式错误 | `bootstrap.py:190-192` `env = { KEY = "${KEY}" }` | TOML 不做 `${}` 插值，拿到字面量 |
| 7 | 非幂等 | 无 checksum 追踪 | 跑两次 `--force` 全量重写 |

### 根本矛盾

```
当前范式：canonical --(copy)--> 工具    [单向、无反馈]
目标范式：canonical <--> 工具            [双向、有 drift 检测]
```

真正的 dotfiles 工具（chezmoi、GNU stow）都是**双向同步 + 链接优先**。当前架构只是"生成器"，不是"同步器"。

## 二、目标架构：四命令闭环

### 命令矩阵

| 命令 | 方向 | 职责 | 幂等 |
|---|---|---|---|
| `apply` | canonical → 工具 | 推有变更的文件到工具目录；创建指令文件；注入密钥 | ✅ checksum 对比 |
| `collect` | 工具 → canonical | 检测工具新增/改动的 skill，回灌到 canonical | ✅ |
| `diff` | 双向 | 对比 canonical 与指定工具，报 drift | 只读 |
| `doctor` | 自检 | canonical 健康度 + skill 引用 + 工具 drift 概览 | 只读 |

### 统一入口

```
python sync.py apply   --canonical <path> --tool <tool> [--write]
python sync.py collect --canonical <path> --tool <tool> [--write]
python sync.py diff    --canonical <path> --tool <tool>
python sync.py doctor  --canonical <path> [--tool <tool>]
```

- 不带 `--write` 默认 dry-run（只打印计划，不落盘）
- `--tool all` 对所有已配置工具执行

## 三、数据结构设计

### 3.1 manifest.json（同步状态追踪）

路径：`canonical/.sync/manifest.json`

```json
{
  "version": 1,
  "generated_at": "2026-08-18T19:00:00+08:00",
  "files": {
    "skills/agent-dev-kit/SKILL.md": {
      "sha256": "a1b2c3...",
      "size": 4523,
      "type": "skill"
    },
    "mcp/mcp.servers.json": {
      "sha256": "d4e5f6...",
      "size": 891,
      "type": "mcp"
    },
    "hooks/secret_scan.py": {
      "sha256": "g7h8i9...",
      "size": 2100,
      "type": "hook"
    }
  },
  "tools": {
    "workbuddy": {
      "last_apply": "2026-08-18T18:30:00+08:00",
      "synced_files": 34,
      "drifted_files": 0
    },
    "cursor": {
      "last_apply": "2026-08-15T10:00:00+08:00",
      "synced_files": 30,
      "drifted_files": 4
    }
  }
}
```

**设计要点**：
- `files` 记录 canonical 侧每个文件的 SHA256
- `tools` 记录每个工具的上次同步时间 + drift 计数
- apply 前对比 canonical 文件 SHA256 vs manifest → 只推有变更的
- collect 后更新 manifest → 记住"工具里有什么"

### 3.2 .env（密钥注入）

路径：`~/.agent-dotfiles/.env`（不入仓库，gitignore）

```bash
# MCP 密钥（apply 时注入，不留 ${} 占位）
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx
DATABASE_URI=postgresql://user:pass@host:5432/db
SQLITE_DB=/path/to/db.sqlite
ALLOWED_DIR=/home/user/projects
```

**apply 流程**：
1. 读 `mcp/mcp.servers.json`
2. 把 `${KEY}` 替换成 `.env` 里的真实值
3. 写入目标工具的配置文件
4. **canonical 里的 `.servers.json` 仍保留 `${}` 占位**（安全）

### 3.3 工具指令文件模板

每个工具需要一个**可执行的指令文件**（当前只是文档，不执行）：

| 工具 | 指令文件 | 内容 |
|---|---|---|
| workbuddy | `AGENTS.md`（仓库根） | 直接复制 canonical AGENTS.md |
| claude | `~/.claude/CLAUDE.md` | 写一行 `@<canonical_path>/AGENTS.md`（引用，不复制） |
| cursor | `~/.cursorrules` | 薄摘要 + `See: <canonical>/AGENTS.md` |
| codex | `~/.codex/AGENTS.md` | 复制 canonical AGENTS.md |
| opencode | `~/.config/opencode/AGENTS.md` | 复制 |
| zed | `~/.config/zed/AGENTS.md` | 复制 |

**apply 时自动创建**，不再需要手动。

## 四、命令接口详细设计

### 4.1 apply

```
python sync.py apply --canonical <path> --tool <tool> [--write] [--force]
```

**流程**：
1. 加载 canonical manifest（无则首次生成）
2. 对比 canonical 每个文件的 SHA256 vs manifest
3. 变更集 = {新增, 修改}；不变 = {SHA256 相同}
4. 对变更集：
   - skills/ → 工具 skills/ 目录（copy 或 symlink）
   - mcp/ → 翻译成工具格式 + 注入 .env 真实密钥
   - hooks/ → 复制脚本
   - 指令文件 → 创建/更新 CLAUDE.md / .cursorrules 等
5. 更新 manifest

**输出**（dry-run 示例）：
```
[apply] tool: cursor  (~/.cursor)
  [new]  skills/agent-dev-kit/ → ~/.cursor/skills/agent-dev-kit/
  [mod]  mcp/mcp.servers.json → ~/.cursor/mcp.json (注入 4 个密钥)
  [ok]   skills/writing-plans/ (未变更, skip)
  [new]  ~/.cursorrules (创建指令文件)
  summary: 2 新增, 1 修改, 31 未变, 0 冲突
```

### 4.2 collect

```
python sync.py collect --canonical <path> --tool <tool> [--write]
```

**流程**：
1. 扫描工具 skills/ 目录
2. 对比 canonical skills/ → 找出工具独有（canonical 没有）的 skill
3. 把独有的 skill 复制回 canonical
4. 更新 manifest

**输出**：
```
[collect] tool: workbuddy  (~/.workbuddy/skills)
  [new]  sheet-agent → canonical/skills/sheet-agent/ (回灌)
  [new]  tencent-docs → canonical/skills/tencent-docs/ (回灌)
  summary: 2 个新 skill 回灌到 canonical
```

### 4.3 diff

```
python sync.py diff --canonical <path> --tool <tool>
```

**流程**：
1. 对比 canonical vs 工具目录的每个文件
2. 分类：`synced`（一致）/ `drifted`（内容不同）/ `missing`（工具缺）/ `extra`（工具有 canonical 没有）

**输出**：
```
[diff] tool: cursor  (~/.cursor)
  [synced]  30 个文件一致
  [drifted] skills/agent-dev-kit/SKILL.md (canonical 较新)
  [missing] hooks/secret_scan.py (工具目录缺失)
  [extra]   skills/old-experiment/ (canonical 没有, 可能是手动装的)
  summary: 30 synced, 1 drifted, 1 missing, 1 extra
```

### 4.4 doctor（扩展）

在现有 doctor 基础上增加：
- `--tool <tool>` 时执行 drift 检测（调用 diff 逻辑）
- 输出 drift 摘要

## 五、迁移路径（从 bootstrap.py 到 sync.py）

### 阶段 1：修致命缺口（低风险，不改架构）
1. **修缺口 1**：bootstrap.py `--write` 段补上创建 CLAUDE.md / .cursorrules 的代码
2. **修缺口 3**：apply 时从 `.env` 注入密钥，不留 `${}` 占位
3. **修缺口 6**：Codex TOML 改为正确格式（env 值从 shell 注入，不在 TOML 里写 `${}`）
4. **修缺口 7**：加 SHA256 manifest，apply 前对比，相同则 skip

### 阶段 2：加 diff + collect（中风险）
5. **修缺口 5**：实现 diff 命令（只读，无副作用）
6. **修缺口 4**：实现 collect 命令

### 阶段 3：链接优化（可选）
7. **修缺口 2**：apply 时优先用 symlink（Unix）/ junction（Windows），不支持则退化 copy

### 文件变更
```
scripts/
  bootstrap.py  →  sync.py  (重命名, 重构)
  doctor.py     →  合并进 sync.py doctor 子命令 (或保持独立, import diff)
  scan_env.py   →  保持不变
  scaffold.py   →  保持不变
新增:
  .sync/manifest.json  (运行时生成)
  .env.example         (密钥模板, 入仓库)
```

### 向后兼容
- `bootstrap.py` 保留为 `sync.py apply` 的薄包装（`bootstrap.py` 调 `sync.py apply`），老用户不受影响
- 现有 `doctor.py` 的 `--canonical` 参数保持不变

## 六、风险与权衡

| 风险 | 严重度 | 缓解 |
|---|---|---|
| Windows symlink 需要开发者模式/admin | 中 | 不支持时退化 copy + checksum |
| collect 误回灌不该进的 skill（如临时试验） | 中 | collect 默认 dry-run；`--write` 需显式；回灌前列出清单等确认 |
| .env 里的密钥被 apply 写入工具配置文件 | 高 | workbuddy/claude 写 `${}` 占位由工具自己解析；codex/opencode/zed 从 shell env 注入；canonical 永不留真实值 |
| manifest 与实际不一致（手动改了文件没更新 manifest） | 中 | diff 命令做真实文件对比，不只依赖 manifest |
| 架构升级工作量 | 中 | 阶段 1 可独立交付（修 3 个致命缺口），阶段 2/3 后续迭代 |

## 七、不做的事（明确排除）

- **不做 chezmoi/stow 的替代品**：目标是"agent 配置同步"，不是通用 dotfiles 管理
- **不做自动冲突合并**：drift 了就报出来让人决定，不自动 merge
- **不做远程同步**：canonical 仓库用 git 管版本控制，sync.py 只管本地 canonical ↔ 工具
- **不做 skill 版本管理**：skill 是目录级同步，不做文件级 diff/merge

## 八、验收标准

阶段 1 完成后：
- [ ] `apply --tool claude --write` 后 `~/.claude/CLAUDE.md` 真实存在且内容正确
- [ ] `apply --tool codex --write` 后 `config.toml` 的 env 不含 `${}` 字面量
- [ ] 连续跑两次 `apply --tool workbuddy --write`，第二次输出"33 未变, 0 修改"
- [ ] `doctor --tool cursor` 输出 drift 摘要

阶段 2 完成后：
- [ ] 在 workbuddy 装新 skill 后 `collect --tool workbuddy --write` 能回灌到 canonical
- [ ] `diff --tool cursor` 能报出 drifted/missing/extra

---

> **决策点**：review 后选一个阶段开始。阶段 1（修 3 个致命缺口）低风险快收益，阶段 2（双向同步）是架构升级。
