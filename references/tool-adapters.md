# 目标工具薄适配器（adapters）

每个工具只放一个指向 canonical 的薄文件 + 把 MCP 定义翻译成目标格式。拒绝三份拷贝漂移。

## WorkBuddy（当前环境）

- 读：`~/.workbuddy/skills/*/SKILL.md`、`~/.workbuddy/mcp.json`
- 适配：
  - 项目规范放仓库根 `AGENTS.md`（WorkBuddy 原生读取项目级指令）。
  - 个人 skill → `~/.workbuddy/skills/`（symlink 或 copy canonical 的 `skills/`）。
  - MCP → 把 `mcp/mcp.servers.json` 原样写入 `~/.workbuddy/mcp.json`（格式一致，无需翻译）。
  - 密钥从本地 `.env` 回填（`env` 字段引用环境变量名）。

## Claude Code

- 读：`CLAUDE.md`（每会话自动加载）、`~/.claude/skills/`、`~/.claude/settings.json`
- 适配：
  - `CLAUDE.md` 写一行 `@AGENTS.md`（指向 canonical），或薄摘要 + 链接。
  - skill → `~/.claude/skills/`。
  - MCP：Claude Code 用 `claude mcp add` 命令，或写入项目 `.mcp.json`（`mcpServers` JSON 同 Cursor）。
  - 例：`claude mcp add --env KEY=value my-server -e npx -a "-y @server/cli"`

## Cursor

- 读：`.cursor/rules/*.mdc`（按文件类型作用域）、`.cursor/mcp.json`
- 适配：
  - 全局规范放 `~/.cursor/rules/global.mdc`（`description: always`，`alwaysApply: true`），内容指向 canonical AGENTS.md。
  - 细粒度规则按目录/文件类型拆 `.mdc`，只对该范围生效。
  - MCP → `.cursor/mcp.json`（`mcpServers` JSON）。
- 注：Cursor 也原生读仓库根 `AGENTS.md`，可零适配。

## Codex CLI

- 读：`~/.codex/config.toml`、`AGENTS.md`
- 适配：
  - MCP 用 TOML 格式：
    ```toml
    [mcp_servers.my_server]
    command = "npx"
    args = ["-y", "@server/cli"]
    env = { KEY = "value" }
    ```
  - skill 同步到 `~/.codex/skills/`。
  - `AGENTS.md` 原生读取。

## OpenCode

- 配置：`~/.config/opencode/opencode.json`（全局）/ 项目根 `opencode.json`。
- 适配：
  - MCP 放在顶层 `mcp` 键；本地 server `command` 是**数组**、`environment` 承载 env：
    ```json
    {
      "$schema": "https://opencode.ai/config.json",
      "mcp": { "my-server": { "type": "local", "command": ["npx","-y","@server/cli"], "enabled": true, "environment": { "KEY": "${KEY}" } } }
    }
    ```
  - `bootstrap.py` 已翻译并**合并**进已有 `opencode.json`（不覆盖 agents/providers）。
  - skill 复制到 `~/.config/opencode/skills/`（best-effort）；`AGENTS.md` 放 `~/.config/opencode/` 或项目根。
  - 详见 `assets/adapters/opencode.md`。

## Zed

- 配置：`~/.config/zed/settings.json`（全局）/ `.zed/settings.json`（项目）。
- 适配：
  - MCP 放在 **`context_servers`** 键；`command` 是**字符串**、`args` 数组：
    ```json
    { "context_servers": { "my-server": { "command": "npx", "args": ["-y","@server/cli"], "env": { "KEY": "${KEY}" } } } }
    ```
  - `bootstrap.py` 已翻译并**合并**进已有 `settings.json`（不覆盖其他 Zed 设置）。
  - 无 skills 文件夹，用 `/context` 自定义上下文替代；`AGENTS.md` 放 `~/.config/zed/`。
  - 详见 `assets/adapters/zed.md`。

## MCP 翻译要点（通用）

1. 取 canonical `mcp.servers.json` 里每个 server 的 `command` / `args` / `env`。
2. 按目标格式包裹：
   - JSON 工具（Cursor/Claude/VS Code）：直接 `{ "mcpServers": { "name": { command, args, env } } }`。
   - TOML 工具（Codex）：`[mcp_servers.name]` 段。
3. `env` 里的密钥值用环境变量占位（如 `"${API_KEY}"`），从 `.env` 注入，绝不写死。
4. 跑不起来的 server（依赖某工具独占能力）标记 `// TODO: adapt` 并告诉用户，不要静默丢弃。

## Hooks 扇出（自动化护栏）

`hooks/` 目录（3 个工具无关的 Python 脚本 + `hooks.json` 声明）由 `bootstrap.py` 一并复制到
目标工具目录（如 `~/.workbuddy/hooks`、`~/.claude/hooks`、`~/.codex/hooks`）。脚本跨平台，
但**接线方式因工具而异**，详见 `hooks/README.md`：

- `secret-scan`（pre-commit）：提交前扫文件，命中真实密钥即阻断。
- `danger-confirm`（pre-tool-use）：拦截 rm -rf / force push / drop 等，需显式确认。
- `memory-update`（post-task）：任务结束把决策/约定回写 `.agents/memory`。

各工具接线要点：
- **WorkBuddy**：脚本入 `~/.workbuddy/hooks/`，在工作流里绑定触发。
- **Claude Code**：`~/.claude/settings.json` 的 `hooks.PreToolUse` / `PostToolUse` 调命令。
- **Codex**：`~/.codex/config.toml` 的 `[hooks]` 段（`pre-tool-use` / `post-task`）。
- **Cursor**：agent 配置里用 shell 命令绑定，逻辑同上。
- **OpenCode**：`opencode.json` 的 `hooks` 段绑定脚本（参考官方 hooks 文档）。
- **Zed**：agent 配置里以 shell 命令绑定，逻辑同上。

## dotfiles 扇出纪律

- 锁文件是 canonical 仓库的 git 历史；各工具目录只放 symlink/copy 的薄层。
- 改规范只改 canonical，再重新扇出（幂等）。
- 用 `doctor.py` 定期检查各工具层与 canonical 的 drift。
