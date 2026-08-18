# OpenCode 适配器

OpenCode 的配置在 `~/.config/opencode/opencode.json`（全局）或项目根 `opencode.json`。

## 适配要点
- **MCP**：放在顶层 `"mcp"` 键下，本地 server 格式为：
  ```json
  {
    "$schema": "https://opencode.ai/config.json",
    "mcp": {
      "context7": {
        "type": "local",
        "command": ["npx", "-y", "@upstash/context7-mcp"],
        "enabled": true,
        "environment": { "KEY": "${KEY}" }
      }
    }
  }
  ```
  - 注意 `command` 是**数组**（含 npx 与参数合并）；环境变量键是 `environment`（不是 `env`）。
  - `bootstrap.py` 已按此格式翻译并**合并**进已有 `opencode.json`（不覆盖你其他的 agents/providers 配置）。
- **Skills**：OpenCode 无 agent-skills 文件夹概念；把 canonical `skills/` 复制到
  `~/.config/opencode/skills/`（best-effort，按需启用），并把 `AGENTS.md` 放到
  `~/.config/opencode/AGENTS.md` 或项目根。
- **Hooks**：OpenCode 的 hooks 在 `opencode.json` 的 `hooks` 段；本套 `hooks/*.py`
  需自行接线（参考 `hooks/README.md` 的通用 shell 绑定方式）。
- **密钥**：`environment` 的值用 `${VAR}` 占位，从本地 `.env`/shell 注入。
