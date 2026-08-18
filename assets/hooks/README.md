# Hooks（自动化护栏）

> 由 `agent-dev-kit` 维护，跨工具通过 `bootstrap.py` 把 `hooks/` 目录扇出到目标工具目录。
> 脚本是**工具无关的纯 Python**（跨平台），但**接线方式因工具而异**——下面是各工具接线说明。

## 三个 hook
| id | 触发 | 脚本 | 作用 |
|---|---|---|---|
| `secret-scan` | pre-commit | `secret_scan.py` | 提交前扫文件，命中真实密钥即阻断（退出码 1） |
| `danger-confirm` | pre-tool-use | `danger_confirm.py` | 拦截 rm -rf / force push / drop 等，退出码 2 |
| `memory-update` | post-task | `memory_update.py` | 任务结束把决策/约定回写 `.agents/memory/`（退出码 0） |

`hooks.json` 是工具无关的声明；各工具按 `trigger` 映射到自己的 hook 事件。

> ⚠️ **接线前提**：本 `hooks.json` / 各工具 `settings.json` 只是"声明"，**是否真正触发取决于
> 该工具是否加载并支持对应 hook 事件**。接好后在对应工具里实际跑一次验证（见下"已验证生效"）。
> 切勿假设"写了就生效"。

## 已验证生效的接线（本 canonical 仓库）
- **secret-scan**：`agent-dotfiles/.git/hooks/pre-commit` 已安装并实测可阻断含真实密钥的提交
  （对 `.md/.json/.toml/.yaml/.yml/.env/.py/.js/.ts/.txt/.cfg/.ini` 的暂存文件扫描）。
  任何克隆本仓库并保留 `.git/hooks` 的环境，git 提交路径上 secret-scan 默认生效。

## 接线方式

### WorkBuddy
把脚本放入 `~/.workbuddy/hooks/`（bootstrap 已复制）。在工作流/设置里绑定：
- pre-commit → `python hooks/secret_scan.py $(git diff --cached --name-only)`
- pre-tool-use → `python hooks/danger_confirm.py "<command>"`
- post-task → `python hooks/memory_update.py --topic "<名>" --note "<内容>"`
  （**需 agent 显式传入真实内容**；无 `--note`/管道内容时脚本会跳过，不会自动抓取决策）

### Claude Code（`~/.claude/settings.json`）
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "python ~/.claude/hooks/danger_confirm.py \"$CLAUDE_TOOL_INPUT\""
      }]
    }],
    "PostToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "python ~/.claude/hooks/memory_update.py --topic auto --note \"$CLAUDE_TOOL_OUTPUT\""
      }]
    }]
  }
}
```
> 注意：`PostToolUse` 拿不到"本次任务的决策摘要"，`$CLAUDE_TOOL_OUTPUT` 只是工具返回值，
> **不适合直接当记忆内容**。正确做法：让 agent 在任务中判定"值得固化"时主动调用
> `memory_update.py --note "..."`，而非依赖 post-task 自动写。自动写只会落噪声。
（pre-commit 用 `git config core.hooksPath .git/hooks` 指向 secret_scan 包装脚本。）

### Codex CLI（`~/.codex/config.toml`）
```toml
[hooks]
pre-tool-use = "python ~/.codex/hooks/danger_confirm.py \"$TOOL_INPUT\""
# post-task 记忆回写需 agent 显式传 --note，否则 memory_update 会跳过（无内容 no-op）
post-task    = "python ~/.codex/hooks/memory_update.py --topic auto --note \"$TASK_SUMMARY\""
```
（pre-commit 接 git hooks 指向 secret_scan；`$TASK_SUMMARY` 需由调用方提供真实摘要。）

### Cursor（`.cursor/settings.json` 或项目 `.cursorrules`）
Cursor 主要走 MCP / 规则；hooks 通过 `shell` 命令在 agent 配置里绑定，逻辑同上。

## 安全提示
- 脚本只做**本地判断**，不联网、不读外部。
- `danger-confirm` 默认阻断；确需执行危险命令时，由人显式确认后放行。
- `secret-scan` 的误报过滤已排除 `${...}`/`<...>`/示例占位；真实密钥才会阻断。
