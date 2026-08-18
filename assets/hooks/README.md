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

## 接线方式

### WorkBuddy
把脚本放入 `~/.workbuddy/hooks/`（bootstrap 已复制）。在工作流/设置里绑定：
- pre-commit → `python hooks/secret_scan.py $(git diff --cached --name-only)`
- pre-tool-use → `python hooks/danger_confirm.py "<command>"`
- post-task → `python hooks/memory_update.py --topic "<名>" --note "<内容>"`

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
        "command": "python ~/.claude/hooks/memory_update.py --topic auto --note \"$(date)\""
      }]
    }]
  }
}
```
（pre-commit 用 `git config core.hooksPath .git/hooks` 指向 secret_scan 包装脚本。）

### Codex CLI（`~/.codex/config.toml`）
```toml
[hooks]
pre-tool-use = "python ~/.codex/hooks/danger_confirm.py \"$TOOL_INPUT\""
post-task    = "python ~/.codex/hooks/memory_update.py --topic auto"
```
（pre-commit 接 git hooks 指向 secret_scan。）

### Cursor（`.cursor/settings.json` 或项目 `.cursorrules`）
Cursor 主要走 MCP / 规则；hooks 通过 `shell` 命令在 agent 配置里绑定，逻辑同上。

## 安全提示
- 脚本只做**本地判断**，不联网、不读外部。
- `danger-confirm` 默认阻断；确需执行危险命令时，由人显式确认后放行。
- `secret-scan` 的误报过滤已排除 `${...}`/`<...>`/示例占位；真实密钥才会阻断。
